__author__ = 'Nicolas Tomatis'
__version__ = "Version 1.2"
__copyright__ = "Copyright 2016, PydevAr"
__email__ = "pydev.ar@gmail.com"
#12-06-2016 se modifica nombre y fecha
# 07/04/2016 se implementa cliente xml/rpc para transmitir comandos a la RPI que mueve los motores por red
# sin usar conexion por cables ni placa intermedia.

# 23/05/2016 se cambia estrategia de comunicacion con el servidor de motores xml/rpc para que repita siempre
# los mensajes si el servidor esta en modo manual. En ese caso el servidor va a responder con 2 en lugar de 1.

# Configuration options
from config import *

# Constants to be defined.
DEBUG = False  # Use for developers.
SIZE = (640, 480)  # Camera resolution in (x, y)

SHOW_IMAGE = True  # View the camera.

# Python libraries
import time
import cv2
import sys
import datetime
import xmlrpclib    # biblioteca de funciones xml/rpc


FOURCC = cv2.cv.CV_FOURCC(*'XVID')

if not USE_RASPBERRY:
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

    if USE_RASPBERRY:
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
    if USE_RASPBERRY:
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

    if USE_RASPBERRY:
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


def show_center(image, cx, cy):

    cv2.circle(image, (cx, cy), int(CENTER_RADIUS/4), (80, 200, 80), -1)
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

    # Conectamos con el servidor.
    proxy = xmlrpclib.ServerProxy("http://192.168.0.100:8000/")
    orden=0     # orden para los motores

    # When no contour has been detected:
    # It turns on LED_YELLOW and returns ""
    if cx < 0 or cy < 0:
        led_action(available_leds["LED_YELLOW"], "on")
        led_action(available_leds["LED_G_LEFT"], "off")
        led_action(available_leds["LED_G_RIGHT"], "off")
        led_action(available_leds["LED_G_UP"], "off")
        led_action(available_leds["LED_G_DOWN"], "off")
        led_action(available_leds["LED_RED"], "off")
        if (orden != check_quadrant.anterior): #test si transmite orden nueva
            pepe=proxy.set_motores(orden,"Busca")  # motores detenidos
        check_quadrant.anterior=orden
        return result
    else:
        led_action(available_leds["LED_YELLOW"], "off")

    # If the image is centered:
    # It turns on LED_RED
    if abs(cx - SIZE[0]/2) < CENTER_RADIUS and abs(cy - SIZE[1]/2) < CENTER_RADIUS:
        led_action(available_leds["LED_RED"], "on")
        orden=16 #blanco centrado
    else:
        led_action(available_leds["LED_RED"], "off")

    # Turns on green leds, when the contour is at the left / right
    if abs(cx - SIZE[0]/2) < CENTER_RADIUS:
        result = "x-center"
        led_action(available_leds["LED_G_LEFT"], "off")
        led_action(available_leds["LED_G_RIGHT"], "off")
    elif cx < SIZE[0]/2:
        result = "left"
        led_action(available_leds["LED_G_LEFT"], "on")
        led_action(available_leds["LED_G_RIGHT"], "off")
        orden=1
    elif cx > SIZE[0]/2:
        result = "right"
        led_action(available_leds["LED_G_LEFT"], "off")
        led_action(available_leds["LED_G_RIGHT"], "on")
        orden=3

    # Turns on green leds, when the contour is up / down
    if abs(cy - SIZE[1]/2) < CENTER_RADIUS:
        result += " y-center"
        led_action(available_leds["LED_G_UP"], "off")
        led_action(available_leds["LED_G_DOWN"], "off")
    elif cy < SIZE[1]/2:
        result += " up"
        led_action(available_leds["LED_G_UP"], "on")
        led_action(available_leds["LED_G_DOWN"], "off")
        orden=orden+4
    elif cy > SIZE[1]/2:
        result += " down"
        led_action(available_leds["LED_G_UP"], "off")
        led_action(available_leds["LED_G_DOWN"], "on")
        orden=orden+12

    if (orden != check_quadrant.anterior):   #test si transmite orden nueva
        pepe=proxy.set_motores(orden,"Busca")        # mueve motores segun calculo anterior
        if pepe==2:
            check_quadrant.anterior=99
        else:
            check_quadrant.anterior=orden

    # A string is returned with the corresponding place where the contour was detected
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


def record_action(place, frame, take_photo, take_video):
    """
    Take a photo when a contour is detected for the first time.
    Take a photo when a contour is centered for the first time.
    Records a video for a limited time:
        It starts when an object is found,
        It finishes when the object is centered,
        If it takes more than 30 seconds, the video is cut.
    """

    global contour_appeared, contour_centered, record_video, object_appeared, video_writer

    # If there is not contour in the image
    if place == "":
        contour_appeared = False
        contour_centered = False
    # A contour has appeared
    elif not contour_appeared:
        contour_appeared = True
        print "A contour has appeared."

        if take_photo:  # The image is saved if it is explicitly told.
            # When the contour appears a photo is taken
            object_appeared = datetime.datetime.now()
            appeared_txt = "BUSCA_d_S05587_%s.jpg" % object_appeared.strftime('%d-%m-%Y_%H:%M:%S')
            cv2.imwrite(appeared_txt, frame)

        if take_video:  # The video is saved if it is explicitly told.
            # And video starts recording
            record_video = "on"
            video_writer = cv2.VideoWriter("BUSCA_detection_S05587_%s.avi" % object_appeared.strftime('%d-%m-%Y_%H:%M:%S'), FOURCC, 20, SIZE)

    # A contour is centered
    elif not contour_centered and place == "x-center y-center":
        contour_centered = True
        print "A contour is centered."

        if take_photo:
            # When the contour appears a photo is taken
            centered_txt = "BUSCA_centered_S05587_%s.jpg" % datetime.datetime.now().strftime('%d-%m-%Y_%H:%M:%S')
            cv2.imwrite(centered_txt, frame)

        if take_video:
            record_video = "finish"

    if take_video:
        if record_video == "on":
            if (datetime.datetime.now() - object_appeared).seconds <= RECORD_SECONDS:
                # The video is recorded.
                video_writer.write(frame)
            else:
                # The video finishes after 30 seconds.
                print "The video has been saved."
                video_writer.write(frame)
                video_writer.release()
                record_video = "off"
        elif record_video == "finish":
            # The video finishes when it has been centered.
            print "The video has been saved."
            video_writer.write(frame)
            video_writer.release()
            record_video = "off"

def camera_loop():
    """
    Main Loop where the Image processing takes part.
    """
    global contour_appeared, contour_centered, record_video
    camera, stream = set_up_camera()

    # Global variables initialized.
    contour_appeared = False
    contour_centered = False
    record_video = "off"
    check_quadrant.anterior=0  # inicializa valor anterior de orden

    while True:
        frame = capture_frame(camera, stream)
        if frame is None:
            cv2.destroyAllWindows()
            break

        if CORRECT_VERTICAL_CAMERA:
            # To flip camera vertically (only when necessary)
            frame = cv2.flip(frame, 0)

        if CORRECT_HORIZONTAL_CAMERA:
            # To flip camera horizontally (only when necessary)
            frame = cv2.flip(frame, 1)

        original = frame.copy()
        # Shows current frame
        # cv2.imshow("original", original)

        #################### Image processing starts ###########################

        # Change frame to grey color.
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Threshold.
        _dummy, b_frame = cv2.threshold(gray_frame, THRESHOLD, 255, cv2.THRESH_BINARY)
        # cv2.imshow("b_clone", b_frame)

        # Obtain a single contour.
        cx, cy = obtain_single_contour(b_frame)

        # Check in which quadrant the center of the contour is
        # And show it in the leds.
        # Returns the place where the contour is.
        place = check_quadrant(cx, cy)

        # Create coordinates and show them as lines.
        frame = create_coordinates(frame)

        if SHOW_CENTER_CIRCLE:
            # Show center of circle detected
            frame = show_center(frame, cx, cy)


        # Takes photos and videos when contour is detected/centered.
        record_action(place, frame, ENABLE_PHOTO, ENABLE_VIDEO)

        if SHOW_IMAGE:

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

