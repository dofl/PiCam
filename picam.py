import os
import picamera
import picamera.array
import time
import datetime
import time
import logging
import numpy as np
import RPi.GPIO as GPIO
from astral import Astral
from fractions import Fraction

camera = picamera.PiCamera()

# ----------------------- Settings ------------------------------------------------------------

# Image file save loction? No tailing /
# Leave at /mnt/picam_ramdisk when using the storageController.sh
imageFileLocation        = '/mnt/picam_ramdisk'
imageFileLocationOffline = '/mnt/picam_offline'     # Set to None (without '') if not used

# Camera
camera.resolution = (1296, 972)
camera.hflip = False
camera.vflip = False
camera.rotation = 270

imageQuality = 20  # jpg image quality 0-100 (200KB-1.5MB per image)

# Astral location for sunset and sunrise/ Find your nearest city here: http://pythonhosted.org/astral/#cities
astral_location = "Amsterdam"

# LED settings
CamLed = 5  # Use 5 for Model A/B and 32 for Model B+
ledTurnOnTime = "23.00"  # use 24H scheme
ledTurnOffTime = "06:00"  # use 24H scheme

# Motion detection
motionScoreDay = 100
motionScoreNight = 50

imagesToShootAtMotion = 1  # How many images you want when motion is detected?


#-----------------------------------------------------------------------------------------------
# System Initialisation

# Astral
astralLastUpdateTime = datetime.datetime.now() + datetime.timedelta(-1)
astralSunPosition = None    # dictionary with sunrise and sunset
astralIsDay = False

# logging
logging.basicConfig(filename='picam.log', level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger("capture_motion")

# Initiate camera
motionDetected = False
MotionLastStillCaptureTime = datetime.datetime.now()
camera.framerate = 10

# initialise camera LED
GPIO.setmode(GPIO.BCM)
GPIO.setup(CamLed, GPIO.OUT, initial=False)
isCameraLedon = False

#-----------------------------------------------------------------------------------------------
# Get available disk space
def freeSpaceAvailable():
    st = os.statvfs(imageFileLocation + "/")
    diskSpaceFree = st.f_bavail * st.f_frsize
    diskSpaceRequired = 2 * 1024 * 1024
    freeSpaceAvailable = True

    if diskSpaceFree < diskSpaceRequired:
        freeSpaceAvailable = False

    return freeSpaceAvailable

#-----------------------------------------------------------------------------------------------
def UpdateAstral():
    global astralLastUpdateTime, astralSunPosition, astralIsDay
    # Sunrise and Sunset times updates every 24h
    if (astralLastUpdateTime < (datetime.datetime.now() - datetime.timedelta(hours=24))):
        LOG.info("Updating astral because of 24h difference: " + str(datetime.datetime.now() - astralLastUpdateTime))
        astralLastUpdateTime = datetime.datetime.now()

        astralSunPosition = Astral()[astral_location].sun(None, local=True)
        LOG.info("Astral updated to sunrise " + \
                 astralSunPosition['sunrise'].time().strftime('%H:%M') + \
                 " and sunset " + astralSunPosition['sunset'].time().strftime('%H:%M'))

    # Switch between day and night by Astral sunrise and sunset
    if (time.strftime("%H:%M") == astralSunPosition['sunrise'].time().strftime('%H:%M')) and astralIsDay is False:
        astralIsDay = True
        LOG.info("Astral: Uprise of the light")
    if (time.strftime("%H:%M") == astralSunPosition['sunset'].time().strftime('%H:%M')) and astralIsDay is True:
        astralIsDay = False
        LOG.info("Astral: Darkness cometh")


#-----------------------------------------------------------------------------------------------
def UpdateLED():
    global ledTurnOnTime, ledTurnOffTime, isCameraLedon
    # Turn LED on and off
    if (time.strftime("%H:%M") == ledTurnOnTime) and isCameraLedon is False:
        GPIO.output(CamLed, True)
        LOG.info("LED: Turned on")
    if (time.strftime("%H:%M") == ledTurnOffTime) and isCameraLedon is True:
        GPIO.output(CamLed, False)
        LOG.info("LED: Turned off")

#-----------------------------------------------------------------------------------------------
# Day motion detection uses the camera to constantly record and analyse every frame for motion.
# This is quicker then shooting seperate images and comparing.
class DetectMotion(picamera.array.PiMotionAnalysis):
    def analyse(self, a):
        global motionDetected, MotionLastStillCaptureTime, motionScoreDay, motionScoreNight, astralIsDay

	if astralIsDay:
		motionScore = motionScoreDay
	else:
		motionScore = motionScoreNight

        if datetime.datetime.now() > MotionLastStillCaptureTime + \
                datetime.timedelta(seconds=5):
            a = np.sqrt(
                np.square(a['x'].astype(np.float)) +
                np.square(a['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
            #print str((a > 60).sum())
            if (a > 60).sum() > motionScore:
                #LOG.debug('motion detected (%s) at: %s' % datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f'), motionScore)
                motionDetected = True

#-----------------------------------------------------------------------------------------------
def FilenameGenerator():

    filename = None

    if freeSpaceAvailable():
        filename = imageFileLocation + "/" + datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    else:
        if imageFileLocation == "None":
            logging.info('No space left on disk. Will not save image')
        else:
            filename = imageFileLocationOffline + datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')

    logging.debug('Filename generated: %s', filename)

    return filename

#-----------------------------------------------------------------------------------------------
def TakeDayImage():
    # http://picamera.readthedocs.org/en/release-1.10/recipes2.html#capturing-images-whilst-recording

    time.sleep(0.5)   # sleep for a little while so camera can get adjustments

    camera.exposure_mode = 'auto'
    camera.awb_mode = 'auto'

    if imagesToShootAtMotion > 1:
       	camera.capture_sequence([FilenameGenerator() + '_%02d.jpg' % i for i in range(imagesToShootAtMotion)], format='jpeg', quality=imageQuality, use_video_port=True)
    else:
        camera.capture(FilenameGenerator() + ".jpg", 'jpeg', quality=imageQuality, use_video_port=True)

    return

#-----------------------------------------------------------------------------------------------
def TakeNightImage():

    logging.debug("Start night image shot")

    camera.framerate = Fraction(1, 6)
    camera.shutter_speed = 25000000   # 2.5 seconds
    camera.exposure_mode = 'off'
    camera.iso = 700

    time.sleep(2)   # Give the camera a good long time to measure AWB

    if imagesToShootAtMotion > 1:
        camera.capture_sequence([FilenameGenerator() + '_%02d.jpg' % i for i in range(imagesToShootAtMotion)], format='jpeg', quality=imageQuality, use_video_port=False)
    else:
        camera.capture(FilenameGenerator() + ".jpg", 'jpeg', quality=imageQuality, use_video_port=False)

    return

#-----------------------------------------------------------------------------------------------
# Main program initialization and logic loop

print "PiCam started. All logging will go into picam.log"

while True:
    with DetectMotion(camera) as output:
        try:
            camera.start_recording('/dev/null', format='h264', motion_output=output)
            while not motionDetected:
                UpdateAstral()
                UpdateLED()
                camera.wait_recording(1)

	    motionDetected = False

            if astralIsDay:
		TakeDayImage()
            else:
		camera.stop_recording()
                TakeNightImage()
                camera.start_recording('/dev/null', format='h264', motion_output=output)

        except Exception:
            logging.info('Exception', exc_info=True)
        finally:
            logging.info("Motion detection ended")
            camera.stop_recording()

logging.info("PiCam Script ended")

