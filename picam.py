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
global camera
camera = picamera.PiCamera()

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("capture_motion")

# ------ Settings ------

# Camera
camera.resolution       = (1296, 972)
camera.framerate        = 10
camera.hflip            = False
camera.vflip            = False
camera.rotation         = 270
camera.brightness       = 50
camera.sharpness        = 0
camera.contrast         = 0
camera.brightness       = 50
camera.saturation       = 0
camera.ISO              = 0
camera.exposure_mode    = 'auto'

# Astral location for sunset and sunrise
# Find your nearest city here: http://pythonhosted.org/astral/#cities
global astral_location
astral_location         = "Amsterdam"

global astral_lastQueryTime
astral_lastQueryTime    = None

global astral_sunrise
astral_sunrise          = None

global astral_sunset
astral_sunset           = None

# Motion detection
minimum_still_interval          = 5
motion_detected                 = False
last_still_capture_time         = datetime.datetime.now()


# ------ Main  -------

def CheckDayNightCycle():
	global astral_lastQueryTime
	global astral_sunrise
	global astral_sunset

	# SCript is just starting up. Fillup astral_lastQueryTime
	if (astral_lastQueryTime is None):
		astral_lastQueryTime = datetime.datetime.now() + datetime.timedelta(-30)

	# Sunrise and Sunset times updates every 24h
	if (astral_lastQueryTime < (datetime.datetime.now()-datetime.timedelta(hours=24))):
		print "Updating astral because of 24h difference: " + str(datetime.datetime.now() - astral_lastQueryTime)
		astral_lastQueryTime = datetime.datetime.now()
		print astral_lastQueryTime

		astral_sun = Astral()[astral_location].sun(None, local=True)
		astral_sunrise = astral_sun['sunrise']
		astral_sunset = astral_sun['sunset']
		LOG.info("Astral updated to " + str(astral_sunrise) + " | " + str(astral_sunset))

	# Check if we the camera.exposure_mode needs to be changed
	if time.strftime("%H:%M:%S") == astral_sunrise.time():
		camera.exposure_mode = 'auto'
		LOG.info("Changing camera exposure to day (auto)")
	if time.strftime("%H:%M:%S") == astral_sunset.time():
		camera.exposure_mode = 'night'
		LOG.info("Changing camera exposure to night")

# The 'analyse' method gets called on every frame processed while picamera # is recording h264 video.
class DetectMotion(picamera.array.PiMotionAnalysis):
  def analyse(self, a):
    global minimum_still_interval, motion_detected, last_still_capture_time
    if datetime.datetime.now() > last_still_capture_time + \
        datetime.timedelta(seconds=minimum_still_interval):
      a = np.sqrt(
        np.square(a['x'].astype(np.float)) +
        np.square(a['y'].astype(np.float))
      ).clip(0, 255).astype(np.uint8)
      # if there're more than 10 vectors with a magnitude greater
      # than 80, then motion was detected:
      if (a > 80).sum() > 10:
        LOG.info('motion detected at: %s' % datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f'))
        motion_detected = True


CheckDayNightCycle()

with DetectMotion(camera) as output:
  try:
    # record video to nowhere, as we are just trying to detect motion and capture images:
    camera.start_recording('/dev/null', format='h264', motion_output=output)
    while True:
      while not motion_detected:

        # Check if the cam needs to switch to day/night
        CheckDayNightCycle()

        camera.wait_recording(1)

      LOG.info('stop recording and capture an image...')
      camera.stop_recording()
      motion_detected = False

      filename = '/mnt/serv/' + datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f') + '.jpg'
      #camera.capture(filename, 'jpeg')

      LOG.info('image captured to file: %s' % filename)

      # restart video recording
      camera.start_recording('/dev/null', format='h264', motion_output=output)
  except KeyboardInterrupt as e:
    camera.close()
    LOG.info("\nreceived KeyboardInterrupt via Ctrl-C")
    pass
  finally:
    LOG.info("\ncamera turned off!")
    LOG.info("detect motion has ended.\n")

