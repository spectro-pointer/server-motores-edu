__author__ = 'Nicolas Tomatis'
__version__ = "Version 1.3"
__copyright__ = "Copyright 2016, PydevAr"
__email__ = "pydev.ar@gmail.com"


# ------------------------- CAMERA CONFIGURATION ------------------------------ #
USE_RASPBERRY = True
# True when used with a Raspberry, False for debug on PC.

CORRECT_VERTICAL_CAMERA = False
# Use this when camera is upside down only. Options (True/False)

CORRECT_HORIZONTAL_CAMERA = False
# Use this when camera is showing mirrored image only. Options (True/False)

# ------------------------- IMAGE CONFIGURATION ------------------------------- #
CENTER_RADIUS =5
# Radius of circle that is detected. Unit is pixels.
# The center of the light circle must be within this radius to appear as centered.

SHOW_CENTER_CIRCLE = True
# Shows the center of the circle detected.

THRESHOLD = 100
# Threshold of brightness of lights to be detected (Range 0: darkest - 255 brightest)
MINIMUM_AREA = 5
# Minimum area of spheres to detec

# ---------------------------- OUTPUT FILES --------------------------------- #
ENABLE_PHOTO = False
# When set to True, photos are taken when the object appears, and is centered.

ENABLE_VIDEO = False
# When set to True, a video is taken starting when the object appears and finishes when the object
# is centered. The video takes a limited times of seconds, if that time passes, the video is cut.

RECORD_SECONDS = 30
# Number of seconds the video will last as maximum.
WAITING_SECONDS = 5
# Number of seconds that the camera will stay centered
