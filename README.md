# Hey so I've recovered the appdata I needed and thus work on this script is slowed



## The script at scratch/pve_recovery.py will scan all block volumes in a folder, 
## create mountpoints for all non swap volumes with an identifiable filesystem type and then mount them.
## it will then extract the machine id and scan the mounted drives to gather host information (currently only hostname and os name/version)
## Finally, it will save all of the gathered information to a sqlite database

## scratch/volume_to_appdata.py will scan a root folder for docker volumes and will tar them into a directory suitible for a bind mount later
## it parses the volume information from the volume folder name and will replace the first part of the name with the stack name using '_' as a separator
## this is kinda rigid and only works because of the way I named my volumes/appdata bind mounts. Feel free to adapt it to your own setup

### Both of these scripts need to be run as root in order to use the blkid and mount commands.


## The scripts in the root folder are an initial attempt at splitting out the functionality to continue writing in a more readable way
## I started getting in the weeds a bit though and what I had initially in scratch/pve_recovery.py was enough to get enough information for me to recover my appdata
## Mounting the LXC volumes and extracting the host information was easy (thats what this script does), but if a disk from a VM has multiple partitions, it will be recognized as an unknown filesystem by blkid. To mount these you need to use libguestfs and guestmount by passing the block device file as if it was an image file. From there, you can access the partitions and mount them. It might take a bit of guesswork to find the right partition inside the volume, but typically its sda2 if you installed an iso manually through the web interface.

Hi yeah my proxmox cluster broke and I'm trying to fix it. There's no turnkey tools for this, so I'm making a helper script to make it easier.

Very WIP and kinda messy while I prototype

Non-exhaustive dependencies:
- python
- qemu-img
- lvm2
- guestmount
- libguestfs
- libguestfs-tools
- probably more, I'm running this on Debian 12 and haven't tried other distros