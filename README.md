# Summary
PiCam script with focus on image quality, easy setup and a lot of (automatic) functions.

# What works
- Takes images based on motion detection
- Automatically changes day/night settings based on your local sunset/sunrise

# ToDo
The script is still in the works, but a lot is coming:
- Optimal dynamic motion detection level
- Camera LED on/off during the night/day
- Easy installer (although the script isn't hard to install..)
- Website to manage the script / see the recently taken images.
- Multithreading

See the issues list for full details.

# How to install
Make sure you have a Raspberry Pi with the camera addon and a fully updated Raspbian OS. Enable the camera addon in Raspbian:

'sudo raspi-config'
Select Enable camera and hit Enter, then go to Finish and you'll be prompted to reboot.

Install Astral (used for the sunset/sunrise, https://pythonhosted.org/astral)

'sudo pip install astral'

Install Screen

'sudo apt-get install screen'

open the script with a text editor like Nano and edit the values you'd need.

Run the script, preferrable in Screen:

'sudo screen python picam.py'
And ALT-D yourself out of the screen shell and see the images come in.
