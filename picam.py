import io
import picamera
import picamera.array
import RPi.GPIO as GPIO
import subprocess
import Image
import time
import math
from PIL import ImageChops, ImageChops
import datetime
import logging
import numpy as np

# Initiate Camera library
camera = picamera.PiCamera()

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("capture_motion")

# --- Settings

camera.resolution 		= (1280, 1024)
camera.framerate		= 30
camera.hflip 			= False
camera.vflip 			= False
camera.rotation			= 270
camera.brightness 		= 50
camera.sharpness 		= 0
camera.contrast 		= 0
camera.brightness 		= 50
camera.saturation 		= 0
camera.ISO 			= 0
camera.video_stabilization 	= False
camera.exposure_compensation 	= 0
camera.exposure_mode 		= 'auto'


# Initialize Camera LED. default = off
GPIO.setmode(GPIO.BCM)
CAMLED = 32	 # Use 5 for Model A/B and 32 for Model B+
GPIO.setup(CAMLED, GPIO.OUT, initial=False)
GPIO.output(CAMLED,False)



minimum_still_interval = 5
motion_detected = False
last_still_capture_time = datetime.datetime.now()

# The 'analyse' method gets called on every frame processed while picamera
# is recording h264 video.
# It gets an array (see: "a") of motion vectors from the GPU.
class DetectMotion(picamera.array.PiMotionAnalysis):
  def analyse(self, a):
    global minimum_still_interval, motion_detected, last_still_capture_time
    if datetime.datetime.now() > last_still_capture_time + \
        datetime.timedelta(seconds=minimum_still_interval):
      a = np.sqrt(
        np.square(a['x'].astype(np.float)) +
        np.square(a['y'].astype(np.float))
      ).clip(0, 255).astype(np.uint8)
      # experiment with the following "if" as it may be too sensitive ???
      # if there're more than 10 vectors with a magnitude greater
      # than 60, then motion was detected:
      if (a > 10).sum() > 10:
        LOG.info('motion detected at: %s' % datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f'))
        motion_detected = True


with DetectMotion(camera) as output:
  try:
    # record video to nowhere, as we are just trying to detect motion and capture images:
    camera.start_recording('/dev/null', format='h264', motion_output=output)
    while True:
      while motion_detected == True:

	LOG.info('stop recording and capture an image...')
	camera.stop_recording()
 	motion_detected = False

      # save image on the pi locally:
	filename = '/mnt/serv/' + \
	  datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f') + '.jpg'
	camera.capture(filename, format='jpeg', use_video_port=False)
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


GPIO.cleanup()
