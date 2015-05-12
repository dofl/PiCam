# Summary
Better PiCam script with focus on image quality.

# What works
- It shoots motion based images based on a very static config. Hurray!

# ToDo
- Make the processing (write image to location) of the images multithreaded
  - Or use a RAM drive with an external script that copies the contents of the RAM drive to a external location
- Use the sunset and sunrise to dynamically change the brightness of the image in day and night.
- Dynamically change the motion level to 'whats expected'. Kinda like 'around x images per hour is expected'
- Make the LED turn on at night and off during the day
- Create a Python installer for easy install
- Website on the Pi to show the last x images
