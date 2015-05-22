#! /bin/sh

RAMDISK="/mnt/picam_ramdisk"	# ramdisk location
OFFLINE="/mnt/picam_offline"	# temporary offline storage
NETWORK="/mnt/serv"		# network storage location

SERVER_IP="192.168.1.10"	# ip of your server
SERVER_USERNAME="MoCam"
SERVER_PASSWORD="NC700xCam"
SERVER_FOLDER="MoCam"		# the shared folder on the server

PICAM_SCRIPT_NAME="picam.py"
PICAM_SCRIPT_LOCATION="/home/pi"

# create the ramdisk and offline location if not found
if [ ! -d $RAMDISK ]; then
	echo "Creating  RAMDISK folder"
	sudo mkdir $RAMDISK
fi

if [ ! -d $OFFLINE ]; then
	echo "Creating OFFLINE folder"
        sudo mkdir $OFFLINE
fi

# mount the ramdisk
if ! grep -qs $RAMDISK /proc/mounts; then
	sudo mount -t tmpfs -o size=20m tmpfs $RAMDISK
fi

echo "$(date) - Startup done. Starting the constant copy"

while :
do
	DATE=$(date +"%m-%d-%Y %T")

	# check the network location where the images are send to
	ping -c 1 $SERVER_IP > /dev/null
	if ! [ $? -eq 0 ]; then
		echo "$DATE - server IP down. Umounting network folder"
		# server offline. unmount share so images go to the offline location
		sudo umount -l $NETWORK
	else
		# server is up. mount if neccesary
		if ! grep -qs $NETWORK /proc/mounts; then
			sudo mount -t cifs -o username=$SERVER_USERNAME,password=$SERVER_PASSWORD //$SERVER_IP/$SERVER_FOLDER $NETWORK
			echo "$DATE - server IP up, mounted the network share"
		fi
	fi

	# check if the picam script/process is still alive
	sudo ps ax | grep -v grep | grep "$PICAM_SCRIPT_NAME" > /dev/null
	if ! [ $? -eq 0 ]; then
	  	echo "$DATE - PiCam down. Restarting script in 5 seconds"
		sleep 5
		sudo screen -d -m python $PICAM_SCRIPT_LOCATION/$PICAM_SCRIPT_NAME
	fi


	# move files to the network location if mounted, else to offline storage
        if grep -qs "$NETWORK" /proc/mounts; then
		for image in $(find $RAMDISK -type f -mmin +0.05); do
			if ! fuser $image
			then
				mv $image $NETWORK
			fi
		done

		for image in $(find $OFFLINE -type f -mmin +0.05); do
                        if ! fuser $image
			then
                                mv $image $NETWORK
			fi
                done
        else
		for image in $(find $RAMDISK -type f -mmin +0.05); do
                        if ! fuser $image
			then
                                mv $image $OFFLINE
			fi
                done
        fi

        sleep 3
done

