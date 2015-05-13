import io
import picamera
import picamera.array
import time
from PIL import ImageChops, ImageChops
import datetime
import logging
import numpy as np
from astral import Astral
from sys import exit

# Initiate basics
camera = picamera.PiCamera()

logging.basicConfig(filename='picam.log', level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger("capture_motion")

# ------ Settings ------

# Save images to which file loction? No tailing /
# Leave at /mnt/picam_ramdisk when using the storageController.sh
imageFileLocation	= '/mnt/picam_ramdisk'
#imageFileLocation      = '/mnt/serv'

# Camera
camera.resolution       = (1296, 972)
camera.framerate        = 10
camera.hflip            = False
camera.vflip            = False
camera.rotation         = 270
camera.brightness       = 50
camera.sharpness        = 0
camera.contrast         = 0
camera.saturation       = 0
camera.ISO              = 0
camera.exposure_mode    = 'auto'
camera.shutter_speed	= 0

imageQuality		= 15	# jpg image quality 0-100 (200KB-1.5MB per image)

# Astral location for sunset and sunrise
# Find your nearest city here: http://pythonhosted.org/astral/#cities
astral_location         = "Amsterdam"

# Motion detection
motion_score			= 70		# Play with me
imagesToShootAtMotion   	= 1 		# How many images you want when motion is detected?
minimum_still_interval          = 5

# ------ Main  -------

astral_sunrise          = None
astral_sunset           = None
astral_lastQueryTime 	= datetime.datetime.now() + datetime.timedelta(-30)

motion_detected                 = False
last_still_capture_time         = datetime.datetime.now()


def CheckDayNightCycle():
	global astral_lastQueryTime, astral_sunrise, astral_sunset, camera

	# Sunrise and Sunset times updates every 24h
	if (astral_lastQueryTime < (datetime.datetime.now()-datetime.timedelta(hours=24))):
		LOG.info("Updating astral because of 24h difference: " + str(datetime.datetime.now() - astral_lastQueryTime))
		astral_lastQueryTime = datetime.datetime.now()

		astral_sun 	= Astral()[astral_location].sun(None, local=True)
		astral_sunrise 	= astral_sun['sunrise']
		astral_sunset 	= astral_sun['sunset']

		LOG.info("Astral updated to sunrise " + str(astral_sunrise) + " and sunset " + str(astral_sunset))

	# Switch between day and night
	
	if (time.strftime("%H:%M:%S") == astral_sunrise.time()) and camera.exposure_mode != "auto":
		camera.exposure_mode 	= 'auto'
		motion_score 		= motion_score + 20
		#camera.brightness	= camera.brightness - 10 
		camera.shutter_speed    = 0
		LOG.info("Changing camera exposure to day (auto) and motion score to " + motion_score)
	if (time.strftime("%H:%M:%S") == astral_sunset.time()) and camera.exposure_mode != "night":
		camera.exposure_mode 	= 'night'
		motion_score 		= motion_score - 20
		#camera.brightness       = camera.brightness + 10
		camera.shutter_speed    = 50000
		LOG.info("Changing camera exposure to night and motion score to: " + motion_score)

# The 'analyse' method gets called on every frame processed while picamera # is recording h264 video.
class DetectMotion(picamera.array.PiMotionAnalysis):
  def analyse(self, a):
    global minimum_still_interval, motion_detected, last_still_capture_time, motion_score
    if datetime.datetime.now() > last_still_capture_time + \
        datetime.timedelta(seconds=minimum_still_interval):
      a = np.sqrt(
        np.square(a['x'].astype(np.float)) +
        np.square(a['y'].astype(np.float))
      ).clip(0, 255).astype(np.uint8)
      # if there're more than 10 vectors with a magnitude greater than motion_score, then motion was detected:
      if (a > motion_score).sum() > 10:
        LOG.debug('motion detected at: %s' % datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f'))
        motion_detected = True

print "PiCam started. All logging will go into picam.log"

with DetectMotion(camera) as output:
    try:
	# record video to nowhere, as we are just trying to detect motion and capture images:
	camera.start_recording('/dev/null', format='h264', motion_output=output)
        while True:
            while not motion_detected:
                # Check if the cam needs to switch to day/night
                CheckDayNightCycle()
                camera.wait_recording(1)

            #LOG.info('stop recording and capture an image...')
            camera.stop_recording()
            motion_detected = False

            # Shoot as many images as set in the config
            for x in range(0, (imagesToShootAtMotion +1)):
                filename = imageFileLocation + "/" +  datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f') + '.jpg'
            	camera.capture(filename, 'jpeg', quality=imageQuality)

            #LOG.debug('image captured to file: %s' % filename)

            # restart video recording
            camera.start_recording('/dev/null', format='h264', motion_output=output)
    except Exception:
	logging.info('Exception', exc_info=True)
        camera.close()
        pass
    finally:
        LOG.info("camera turned off!")
        LOG.info("detect motion has ended.\n")
