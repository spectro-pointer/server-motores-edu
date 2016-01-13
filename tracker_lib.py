__author__ = 'Nicolas Tomatis'
__version__ = "Version 1.0"
__copyright__ = "Copyright 2015, PydevAr"
__email__ = "pydev.ar@gmail.com"

# Constants to be defined.
DEBUG = False
DEBUG_IMAGES = True
RASPI = True  # True when used with a Raspberry, False for debug on PC.
SIZE = (640, 480)  # (x, y)
CENTER_RADIUS = 20
THRESHOLD = 50
CORRECT_VERTICAL_CAMERA = True  # Use this when camera is upside down only.

# Python libraries
import time
import cv2
import numpy as np
from os import listdir
import sys

if not RASPI:
    GPIO = None
else:
    try:
        # Raspberry Pi Library
        import RPi.GPIO as GPIO

        from picamera.array import PiRGBArray
        from picamera import PiCamera
    except ImportError:
        print "Error: picamera module not recognized. Make sure you are using a Raspberry."
        print "Also make sure that you have installed the following module: pip install picamera[array]"
        sys.exit(0)


def set_up_leds():
    """
    Configures leds as output
    And creates a dictionary with leds configured by HW.
    """
    global available_leds

    if RASPI:
        # BCM convention is to be used.
        GPIO.setmode(GPIO.BCM)

        # This tells Python not to print GPIO warning messages to the screen.
        GPIO.setwarnings(False)

    # Pins sorted with NAMES.
    available_leds = {
        "LED_YELLOW": 18,
        "LED_RED": 24,
        "LED_G_RIGHT": 23,
        "LED_G_LEFT": 27,
        "LED_G_UP": 22,
        "LED_G_DOWN": 17
    }
    if RASPI:
        for led in available_leds.values():
            if DEBUG:
                print "led %i is configured as output" % led
            GPIO.setup(led, GPIO.OUT)


def led_action(led, status):
    """
    Function to turn on/off the leds
    :param led = number of GPIO port
    :param status = string 'on'/'off'
    :return 0 when correctly, -1 when error.
    """
    if DEBUG:
        print led, status
    if led not in available_leds.values():
        print "Led not found:", led
        return -1

    if RASPI:
        if status == "on":
            GPIO.output(led, GPIO.HIGH)
        elif status == "off":
            GPIO.output(led, GPIO.LOW)
        else:
            print "Unknown command:", status
    return 0


def blink(led):
    """
    A led blinks for .5ms
    """
    led_action(led, "on")
    time.sleep(.5)
    led_action(led, "off")


def sequence_test():
    """
    This function is used only to test the leds of the Raspberry Pi Board
    """
    global available_leds
    print sequence_test.__doc__
    print "yellow led will blink..."
    blink(available_leds["LED_YELLOW"])

    print "now red led will blink..."
    blink(available_leds["LED_RED"])

    print "now the green led will blink in clockwise..."
    blink(available_leds["LED_G_UP"])
    blink(available_leds["LED_G_RIGHT"])
    blink(available_leds["LED_G_DOWN"])
    blink(available_leds["LED_G_LEFT"])

    print "The sequence has concluded."


def set_up_camera():
    """
    Initializes Raspberry Pi Camera.
    :returns: (camera, stream)
    """
    print "Press 2 to exit, 3 to stop, 4 to continue"
    try:
        camera = PiCamera()
        camera.resolution = SIZE
        stream = PiRGBArray(camera, size=SIZE)
        time.sleep(0.1)  # allow the camera to warmup
    except:
        print "Error with Raspberry Pi Camera"
        sys.exit(0)
    return camera, stream


def capture_frame(camera, stream):
    """
    Captures Current Frame
    This function should be called inside a loop.
    :returns: frame"""
    frame = None
    try:
        camera.capture(stream, format='bgr', use_video_port=True)
        frame = stream.array
    except:
        print "Error with camera.capture"
    return frame


def wait_key():
    """
    Waits for a key interruption for 1 ms.
    It should be used to show current frame.
    :key 1: Program exits.
    :key 2: The main loop breaks.
    :key 3: The program is paused.
    :key 4: The program is continued.
    """
    keypressed = cv2.waitKey(1) & 0xFF
    if keypressed == ord('1'):
        print "The program is exited by Key Interruption."
        sys.exit()
    elif keypressed == ord('2'):
        cv2.destroyAllWindows()
        return "break"
    elif keypressed == ord('3'):
        while keypressed != ord('4'):
            keypressed = cv2.waitKey(1) & 0xFF
    return ""


def create_coordinates(image):

    cv2.line(image, (0, SIZE[1]/2), (SIZE[0], SIZE[1]/2), (255, 0, 0), 1)
    cv2.line(image, (SIZE[0]/2, 0), (SIZE[0]/2, SIZE[1]), (255, 0, 0), 1)
    cv2.putText(image, "A+", (SIZE[0]/4, SIZE[1]/4), cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 200))
    cv2.putText(image, "B+", (3 * SIZE[0]/4, SIZE[1]/4), cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 200))
    cv2.putText(image, "A-", (SIZE[0]/4, 3 * SIZE[1]/4), cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 200))
    cv2.putText(image, "B-", (3 * SIZE[0]/4, 3 * SIZE[1]/4), cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 200))
    cv2.circle(image, (SIZE[0]/2, SIZE[1]/2), CENTER_RADIUS, (80, 80, 200), 1)
    return image


def camera_test():
    """
    This function is used only to test the Picamera of the Raspberry Pi Board
    """
    camera, stream = set_up_camera()
    while True:
        frame = capture_frame(camera, stream)
        if frame is None:
            cv2.destroyAllWindows()
            break

        cv2.imshow("image", frame)

        if wait_key() == "break":
            break
        # reset the stream before the next capture
        stream.seek(0)
        stream.truncate()
    cv2.destroyAllWindows()


def check_quadrant(cx, cy):
    """
    Obtain in which quadrant the light is,
    and turn on corresponding leds:
    Green shows the positioning.
    Red shows that the camera is centered.
    """
    global available_leds

    # print cx, cy
    result = ""
    if cx < 0 or cy < 0:
        return result

    if abs(cx - SIZE[0]/2) < CENTER_RADIUS and abs(cy - SIZE[1]/2) < CENTER_RADIUS:
        led_action(available_leds["LED_RED"], "on")
    else:
        led_action(available_leds["LED_RED"], "off")

    if abs(cx - SIZE[0]/2) < CENTER_RADIUS:
        result = "x-center"
        led_action(available_leds["LED_G_LEFT"], "off")
        led_action(available_leds["LED_G_RIGHT"], "off")
    elif cx < SIZE[0]/2:
        result = "left"
        led_action(available_leds["LED_G_LEFT"], "on")
        led_action(available_leds["LED_G_RIGHT"], "off")
    elif cx > SIZE[0]/2:
        result = "right"
        led_action(available_leds["LED_G_LEFT"], "off")
        led_action(available_leds["LED_G_RIGHT"], "on")

    if abs(cy - SIZE[1]/2) < CENTER_RADIUS:
        result += " y-center"
        led_action(available_leds["LED_G_UP"], "off")
        led_action(available_leds["LED_G_DOWN"], "off")
    elif cy < SIZE[1]/2:
        result += "up"
        led_action(available_leds["LED_G_UP"], "on")
        led_action(available_leds["LED_G_DOWN"], "off")
    elif cy > SIZE[1]/2:
        result += "down"
        led_action(available_leds["LED_G_UP"], "off")
        led_action(available_leds["LED_G_DOWN"], "on")
    return result


def obtain_single_contour(b_frame):
    """
    Obtain the x and y coordinates of a single contour.
    When none is found, it returns: (-1, -1)
    """
    contours, _h = cv2.findContours(b_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cx, cy = (-1, -1)  # When none is found, a negative coordinates are returned.
    for blob in contours:
        M = cv2.moments(blob)
        if M['m00'] != 0:
            cx, cy = int(M['m10']/M['m00']), int(M['m01']/M['m00'])
    return cx, cy

def camera_loop():
    """
    Main Loop where the Image processing takes part.
    """
    camera, stream = set_up_camera()
    while True:
        frame = capture_frame(camera, stream)
        if frame is None:
            cv2.destroyAllWindows()
            break

        if CORRECT_VERTICAL_CAMERA:
            # To rotate image 180 degrees (only when necessary)
            frame = cv2.flip(frame,0)
        original = frame.copy()
        # Shows current frame
        # cv2.imshow("original", original)

        #################### Image processing starts ###########################

        # Change frame to grey.
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Threshold.
        _dummy, b_frame = cv2.threshold(gray_frame, THRESHOLD, 255, cv2.THRESH_BINARY)
        # cv2.imshow("b_clone", b_frame)

        # Obtain a single contour.
        cx, cy = obtain_single_contour(b_frame)

        # Check in which quadrant the center of the contour is
        # And show it in the leds.
        check_quadrant(cx,cy)

        # Create coordinates and show them as lines.
        frame = create_coordinates(frame)
        lst = list()
        lst.append((frame, "frame"))
        show_images(lst, SIZE)
        # cv2.imshow("frame", frame)

        if wait_key() == "break":
            break
        # reset the stream before the next capture
        stream.seek(0)
        stream.truncate()
    cv2.destroyAllWindows()


def show_images(lst, size):
    """
    Input: List of tuples containing frame and name.
    It shows a list of images one after the other one, with an specified size.
    Each window has it's own name, and each name must bbe different from each other.
    """
    counter = 0
    for frame, name in lst:
        resized_frame = cv2.resize(frame, size)
        cv2.imshow(name, resized_frame)
        cv2.moveWindow(name, size[0]*(counter % 4), (size[1]+35)*((counter / 4) % 3))
        counter += 1

def fun():
    """
    Code to test leds and camera.
    This function doesn't need to be used in the main loop.
    """
    set_up_leds()
    sequence_test()
    camera_test()

    # when code ends, the GPIO is freed...
    GPIO.cleanup()
    print "The program ended successfully."

if __name__ == "__main__":
    fun()
