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
	sudo mount -t tmpfs -o size=40m tmpfs $RAMDISK
fi

echo "Startup done. Starting the constant copy"

while :
do
	# check if server is up
	ping -c 1 $SERVER_IP > /dev/null
	if ! [ $? -eq 0 ]; then
		# server offline. unmount share so images go to the offline location
		sudo umount -l $NETWORK
	else
		# server is up. mount if neccesary
		if ! grep -qs $NETWORK /proc/mounts; then
			sudo mount -t cifs -o username=$SERVER_USERNAME,password=$SERVER_PASSWORD,rw,nounix,iocharset=utf8,file_mode=0777,dir_mode=0777 //$SERVER_IP/$SERVER_FOLDER $NETWORK
		fi
	fi

	# move files to the network location if mounted, else to offline storage
	# files will only be moved if their older then 10 seconds
        if grep -qs $NETWORK /proc/mounts; then
                find $RAMDISK -type f -mmin +0.10 -exec mv "{}" $NETWORK \; -exec sleep 0.1 \; | xargs -n 1 -0 -I {}
                find $OFFLINE -type f -mmin +0.10 -exec mv "{}" $NETWORK \; -exec sleep 0.1 \; | xargs -n 1 -0 -I {}
        else
                find $RAMDISK -type f -mmin +0.10 | xargs -n 1 -0 -I {} mv "{}" $OFFLINE; sleep 1
        fi

        sleep 3
done

