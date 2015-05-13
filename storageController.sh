#! /bin/sh

RAMDISK="/mnt/picam_ramdisk"	# ramdisk location
OFFLINE="/mnt/picam_offline"	# temporary offline storage
NETWORK="/mnt/serv"		# network storage location

SERVER_IP="192.168.1.10"	# ip of your server
SERVER_USERNAME="MoCam"
SERVER_PASSWORD="NC700xCam"
SERVER_FOLDER="MoCam"		# the shared folder on the server

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
	sudo mount -t tmpfs -o size=32m tmpfs $RAMDISK
fi

echo "Startup done. Starting the constant copy"

while :
do
	# check the server who stores the images
	ping -c 1 $SERVER_IP > /dev/null
	if ! [ $? -eq 0 ]; then
		echo "server IP down. umounting and restarting wifi" 
		# server offline. unmount share so images go to the offline location
		sudo umount -l $NETWORK

		# reboot wifi. Could be that this went down
                sudo ifdown --force wlan0
                sleep 10
                sudo ifup --force wlan0
                sleep 10
	else
		# server is up. mount if neccesary
		if ! grep -qs $NETWORK /proc/mounts; then
			sudo mount -t cifs -o username=$SERVER_USERNAME,password=$SERVER_PASSWORD //$SERVER_IP/$SERVER_FOLDER $NETWORK
			echo "server IP up, mounted the network share"
		fi
	fi

	# move files to the network location if mounted, else to offline storage
	# files will only be moved if their older then 10 seconds
        if grep -qs $NETWORK /proc/mounts; then
		for image in $(find $RAMDISK -type f -mmin +0.05); do
			mv $image $NETWORK
		done

		for image in $(find $OFFLINE -type f -mmin +0.05); do
                        mv $image $NETWORK
                done
        else
		for image in $(find $RAMDISK -type f -mmin +0.05); do
                        mv $image $OFFLINE
                done
        fi

        sleep 5
done

