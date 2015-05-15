# Summary
Raspberry Pi (A/B/2) Python Camera script with it's focus on image quality, automation and an easy setup.

# What works
Picam.py
- Takes images based on motion detection
- Automatically changes day/night settings based on your local sunset/sunrise

In combination with the storageController.sh script:
- The picam.py script writes the images to a 32 MB RAMdisk for optimal speed
- Images on the RAMdisk are moved to a network folder, parallel to the pycam.py still shooting images.
- Checks are made to make sure the network location is online. If the network location goes down, images are temporary written to a folder on the SD card until the network folder is back online.

You don't need both scripts, Picam.py can easily run on it's own and write the images to a folder. 

# ToDo
The script is still in the works, but a lot planned:
- Optimal dynamic motion detection level
- Camera LED on/off during the night/day
- Easy installer (although the scripts isn't hard to install..)
- Website to manage the script / see the recently taken images.
See the issues list for full details.

# How to install
Clone this GIT respository on your Raspberry PI:
```
git clone https://github.com/dofl/PiCam.git
```

Install Astral (used for the sunset/sunrise, https://pythonhosted.org/astral)
```
sudo pip install astral
```

Install Screen (to let the scripts run while you log out)
```
sudo apt-get install screen
```

Open the picam.py and storageController.sh scripts with a text editor like Nano and edit the values you'd need.

Run the scripts, preferrably in Screen. Start with the storageController.sh script as this needs to create the RAMdisk first
```
sudo screen sh storageController.sh
sudo screen python picam.py
```
And ALT-D yourself out of the screen shell and see the images come in on your NAS.
If something went wrong or you don't see any images, check the picam.log file.
