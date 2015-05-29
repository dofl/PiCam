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

imageQuality = 15  # jpg image quality 0-100 (200KB-1.5MB per image)

# Astral location for sunset and sunrise/ Find your nearest city here: http://pythonhosted.org/astral/#cities
astral_location = "Amsterdam"
astralIsDay = True	# Start in Day mode

# LED settings
CamLed = 5  # Use 5 for Model A/B and 32 for Model B+
ledTurnOnTime = "23:00"  # use 24H scheme
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

# logging
logging.basicConfig(filename='picam.log', level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger("capture_motion")

# Initiate camera
motionDetected = False
MotionLastStillCaptureTime = datetime.datetime.now()

# initialise camera LED
GPIO.setmode(GPIO.BCM)
GPIO.setup(CamLed, GPIO.OUT, initial=False)
isCameraLedOn = False

#-----------------------------------------------------------------------------------------------
# Get available disk space
def freeSpaceAvailable():
    freeSpaceAvailable = True

    try:
        st = os.statvfs(imageFileLocation + "/")
        diskSpaceFree = st.f_bavail * st.f_frsize
        diskSpaceRequired = 2 * 1024 * 1024 #2 MB

        if diskSpaceFree < diskSpaceRequired:
            freeSpaceAvailable = False
    except Exception:
        LOG.info('Exception', exc_info=True)

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
    if (time.strftime("%H:%M") == astralSunPosition['sunrise'].time().strftime('%H:%M')) and astralIsDay == False:
        astralIsDay = True
        LOG.info("Astral: Uprise of the light")

    if (time.strftime("%H:%M") == astralSunPosition['sunset'].time().strftime('%H:%M')) and astralIsDay == True:
        astralIsDay = False
        LOG.info("Astral: Darkness cometh")

#-----------------------------------------------------------------------------------------------
def UpdateLED():
    global isCameraLedOn
    if (time.strftime("%H:%M") == ledTurnOnTime) and isCameraLedOn == False:
        LOG.info("LED: Turned on")
        GPIO.output(CamLed, True)
	isCameraLedOn = True

    if (time.strftime("%H:%M") == ledTurnOffTime) and isCameraLedOn == True:
        LOG.info("LED: Turned off")
        GPIO.output(CamLed, False)
	isCameraLedOn = False

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
                datetime.timedelta(seconds=1):
            a = np.sqrt(
                np.square(a['x'].astype(np.float)) +
                np.square(a['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
            if (a > 60).sum() > motionScore:
                motionDetected = True

    #-----------------------------------------------------------------------------------------------
def FilenameGenerator():

    filename = None

    if freeSpaceAvailable():
        filename = imageFileLocation + "/" + datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    else:
        if imageFileLocation == "None":
            LOG.info('No space left on disk. Will not save image')
        else:
            filename = imageFileLocationOffline + "/" + datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')

    return filename

#-----------------------------------------------------------------------------------------------
def CameraRecordingSettings():

    camera.framerate = 10
    camera.exposure_mode = 'auto'
    camera.awb_mode = 'auto'
    camera.iso = 0

#-----------------------------------------------------------------------------------------------
def CameraDaySettings():

    camera.exposure_mode = 'auto'
    camera.awb_mode = 'auto'
    camera.iso = 0

#-----------------------------------------------------------------------------------------------
def CameraNightSettings():

    camera.framerate = Fraction(1, 6)
    camera.shutter_speed = 20000000   # 2 seconds
    camera.exposure_mode = 'off'
    camera.iso = 600

#-----------------------------------------------------------------------------------------------
def TakeDayImage():

    time.sleep(0.5)  # sleep for a little while so camera can get adjustments

    if imagesToShootAtMotion > 1:
        camera.capture_sequence([FilenameGenerator() + '_%02d.jpg' % i for i in range(imagesToShootAtMotion)],
                                format='jpeg', quality=imageQuality, use_video_port=False)
    else:
        camera.capture(FilenameGenerator() + ".jpg", 'jpeg', quality=imageQuality, use_video_port=False)

    return
#-----------------------------------------------------------------------------------------------
def TakeNightImage():

    CameraNightSettings()

    time.sleep(2)   # Give the camera a good long time to measure AWB

    if imagesToShootAtMotion > 1:
        camera.capture_sequence([FilenameGenerator() + '_%02d.jpg' % i for i in range(imagesToShootAtMotion)], 
				format='jpeg', quality=imageQuality, use_video_port=False)
    else:
        camera.capture(FilenameGenerator() + ".jpg", 'jpeg', quality=imageQuality, use_video_port=False)

    CameraDaySettings() #Return to default mode for videocapture

    return

#-----------------------------------------------------------------------------------------------
# Main program initialization and logic loop

print "PiCam started. All logging will go into picam.log"

with DetectMotion(camera) as output:
    try:
	CameraRecordingSettings()
        camera.start_recording('/dev/null', format='h264', motion_output=output)
        
        while True:
            while not motionDetected:
                UpdateAstral()
                UpdateLED()
                camera.wait_recording(1)

            motionDetected = False
            camera.stop_recording()
    
            if astralIsDay:
                TakeDayImage()
            else:
                TakeNightImage()

	    MotionLastStillCaptureTime = datetime.datetime.now()
	    CameraRecordingSettings()
	    camera.start_recording('/dev/null', format='h264', motion_output=output)
    except Exception:
        LOG.info('Exception', exc_info=True)
    finally:
        LOG.info("Motion detection ended")
	camera.stop_recording()
        GPIO.cleanup()

logging.info("PiCam Script ended")

