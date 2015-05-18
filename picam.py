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
from PIL import Image

# Initiate basics
camera = picamera.PiCamera()

# ----------------------- Settings ------------------------------------------------------------

# Image file save loction? No tailing /
# Leave at /mnt/picam_ramdisk when using the storageController.sh
imageFileLocation	= '/mnt/picam_ramdisk'

# Camera
#camera.resolution       = (972, 1296)
camera.resolution       = (1296, 972)
#camera.resolution       = (1024, 1280)
camera.framerate        = 10
camera.hflip            = False
camera.vflip            = False
camera.rotation         = 270
camera.ISO              = 150
camera.exposure_mode    = 'auto'
camera.awb_mode 	= 'auto'
camera.shutter_speed	= 0

imageQuality		= 15		# jpg image quality 0-100 (200KB-1.5MB per image)

# Astral location for sunset and sunrise/ Find your nearest city here: http://pythonhosted.org/astral/#cities
astral_location         = "Amsterdam"

# LED settings
CamLed 			= 5      	# Use 5 for Model A/B and 32 for Model B+
ledTurnOnTime		= "23.00"	# use 24H scheme
ledTurnOffTime		= "06:00"	# use 24H scheme

# Motion detection
motion_score		= 80		# Play with me
imagesToShootAtMotion   = 2		# How many images you want when motion is detected?


# ----------------------- Main ---------------------------------------------------------------

logging.basicConfig(filename='picam.log', level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger("capture_motion")

# Camera LED
GPIO.setmode(GPIO.BCM)
GPIO.setup(CamLed, GPIO.OUT, initial=False)

astral_lastQueryTime 		= datetime.datetime.now() + datetime.timedelta(-1)
astral_sun			= None

motion_detected                 = False
last_still_capture_time         = datetime.datetime.now()

ledIsTurnedOn			= False

# Get available disk space
def freeSpaceAvailable():
    st = os.statvfs(imageFileLocation + "/")
    diskSpaceFree = st.f_bavail * st.f_frsize
    diskSpaceRequired = 2 * 1024 * 1024
    freeSpaceAvailable = True
    
    if diskSpaceFree < diskSpaceRequired:
	freeSpaceAvailable = False

    return freeSpaceAvailable

def CheckDayNightCycle():
	global astral_lastQueryTime, astral_sun, camera, motion_score, ledTurnOnTime, ledTurnOffTime

	# Sunrise and Sunset times updates every 24h
	if (astral_lastQueryTime < (datetime.datetime.now()-datetime.timedelta(hours=24))):
		LOG.info("Updating astral because of 24h difference: " + str(datetime.datetime.now() - astral_lastQueryTime))
		astral_lastQueryTime = datetime.datetime.now()

		astral_sun = Astral()[astral_location].sun(None, local=True)
		LOG.info("Astral updated to sunrise " + \
			astral_sun['sunrise'].time().strftime('%H:%M') + \
			 " and sunset " +  astral_sun['sunset'].time().strftime('%H:%M'))

        # Turn LED on and off
	# Can be integrated with the astral if's below, but I find it too early (=scares neighbours)
        if (time.strftime("%H:%M") == ledTurnOnTime) and (ledIsTurnedOn == False):
                GPIO.output(CamLed, True)
		LOG.info("LED turned on")
        if (time.strftime("%H:%M") == ledTurnOffTime) and (ledIsTurnedOn == True):
                GPIO.output(CamLed, False)
		LOG.info("LED turned off")

	# Switch between day and night by Astral sunrise and sunset
	if (time.strftime("%H:%M") == astral_sun['sunrise'].time().strftime('%H:%M')) and camera.exposure_mode == "off":
		camera.exposure_mode 	= 'auto'
		camera.framerate	= 10
		motion_score 		= motion_score + 20
		camera.shutter_speed    = 0
		camera.iso 		= 150
		LOG.info("Changing camera setting to day")
	if (time.strftime("%H:%M") == astral_sun['sunset'].time().strftime('%H:%M')) and camera.exposure_mode == "auto":
		camera.exposure_mode 	= 'off'
		camera.framerate 	= Fraction(1, 6)
		motion_score 		= motion_score - 20
		camera.shutter_speed    = 2000000
		camera.iso 		= 800
		LOG.info("Changing camera setting to night")

# The 'analyse' method gets called on every frame processed while picamera # is recording h264 video.
class DetectMotion(picamera.array.PiMotionAnalysis):
  def analyse(self, a):
    global motion_detected, last_still_capture_time, motion_score
    if datetime.datetime.now() > last_still_capture_time + \
        datetime.timedelta(seconds=5):
      a = np.sqrt(
        np.square(a['x'].astype(np.float)) +
        np.square(a['y'].astype(np.float))
      ).clip(0, 255).astype(np.uint8)
      # if there're more than 10 vectors with a magnitude greater than motion_score, then motion was detected:
      # print str((a > 60).sum()) + " | " + str((a > 80).sum())
      if (a > 60).sum() > motion_score:
	#print "motion"        
	#LOG.debug('motion detected at: %s' % datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f'))
        motion_detected = True

print "PiCam started. All logging will go into picam.log"

with DetectMotion(camera) as output:

    try:
	# record video to nowhere, as we are just trying to detect motion and capture images:
	camera.start_recording('/dev/null', format='h264', motion_output=output)
        while True:
            while not motion_detected:
                CheckDayNightCycle()
                camera.wait_recording(1)

	    # Motion detected
            camera.stop_recording()

	    filename = imageFileLocation + "/" +  datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S_')

	    if freeSpaceAvailable():	
		# Shoot as many images as set in the config
    		camera.capture_sequence([filename + '%02d.jpg' % i for i in range(imagesToShootAtMotion)], format='jpeg', quality=imageQuality)
	    else:
		LOG.info("Free space below 2MB. Couldn't save image!")
		time.sleep(10)

            # restart video recording
	    motion_detected = False
            camera.start_recording('/dev/null', format='h264', motion_output=output)
    except Exception:
	logging.info('Exception', exc_info=True)
        camera.close()
        pass
    finally:
	GPIO.cleanup()
        LOG.info("Camera script shutdown")
