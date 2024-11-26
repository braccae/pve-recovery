import os
import pathlib
from pathlib import Path
import subprocess
import sqlite3
import csv
import time
import tools.db as db
import tools.profile as profile
import tools.mount as mount
import tools.backup as backup

def get_fs_type(device_path):
    """Gets the filesystem type of a block device."""

    try:
        output = subprocess.check_output(["blkid", "-o", "value", "-s", "TYPE", device_path], text=True)
        if output.strip() == "":
            return 'Unknown'
        else: return output.strip()
    except subprocess.CalledProcessError:
        return None

def parse_os_release(path):
  """Parses the /etc/os_release file and returns a dictionary.

  Returns:
      A dictionary containing key-value pairs from the file.
  """
  data = {}
  with open(os.path.realpath(path)) as f:
    reader = csv.reader(f, delimiter="=")
    for key, value in reader:
      data[key.strip()] = value.strip()
  return data

# docker checks
def check_capabilities(root_folder):
    """Checks if Docker is installed."""
    data = {
        'docker_installed': False,
        'has_docker_volumes': False,
        'has_appdata_folder': False
    }
    docker_config = os.path.join(root_folder, '/etc/docker')
    docker_volumes = os.path.join(root_folder, '/var/lib/docker/volumes')
    appdata_folder = os.path.join(root_folder, '/mnt/user/appdata')
    data['docker_installed'] = os.path.exists(docker_config)
    data['has_docker_volumes'] = any(entry.is_dir() for entry in pathlib.Path(docker_volumes).iterdir())
    data['has_appdata_folder'] = os.path.exists(appdata_folder)
    return data

def profile_devices(device_folder):
    device_folder = Path(device_folder)
    devices = sorted([file.name for file in device_folder.iterdir() if file.is_block_device()])
    devices_data = []
    for device in devices:
        device_name = os.path.basename(device)
        fs_type = get_fs_type(device)
        vm_id = -1
        # Unmount the device if it's mounted
        subprocess.run(['umount', device])

        if device_name.startswith('vm-'):
            vm_id = int(device_name[3:device_name.find('-', 3)])
        elif device_name == 'root' or device_name == 'swap':
            vm_id = -999
        else:
            vm_id = -2
        device_data = {
            'name': device_name,
            'path': device,
            'vm_id': vm_id,
            'fs_type': fs_type
        }
        devices_data.append(device_data)
        add_new_device(device_name, device, fs_type, vm_id)
        print(f'Added new device to database!: id: {vm_id} device: {device_name} type: {fs_type} path: {device}')

def profile_hosts(mount_folder_root):

    mounted_filesystems_unsorted = [file.name for file in Path(mount_folder_root).iterdir() if file.is_dir()]
    mounted_filesystems = sorted(mounted_filesystems_unsorted)
    print(mounted_filesystems)

    for mounted_filesystem in mounted_filesystems:

        filesystem_path = str(Path(mount_folder_root)) + '/' + mounted_filesystem
        vm_id = -1
        hostname = ''
        os_name = ''
        os_version = ''
        print(f'checking filesystem: {mounted_filesystem}')
        if not mounted_filesystem.startswith('vm-') and mounted_filesystem != 'root':
            print(f'ignoring {mounted_filesystem} as it doesn\'t look like a vm or the Proxmox root filesystem')
            continue
        elif mounted_filesystem.endswith('-0'):
            print(f'Found a vm root filesystem! Collecting host info...')
            vm_id = int(mounted_filesystem[3:mounted_filesystem.find('-', 3)])
            hostname = subprocess.check_output(['cat', filesystem_path + '/etc/hostname'], text=True).strip()
            print(hostname)
            os_release_info = parse_os_release(filesystem_path + '/etc/os-release')
            os_name = os_release_info['ID']
            os_version = os_release_info['VERSION_ID']
            cap = check_capabilities(filesystem_path)
            if cap['has_docker_volumes']:
                volume_dir = Path(filesystem_path + '/var/lib/docker/volumes')
                docker_volumes = [file.name for file in Path(volume_dir).iterdir() if file.is_dir()]
            if cap['has_appdata_folder']:
                appdata_folder = Path(filesystem_path + '/mnt/user/appdata')
                appdata_folders = [file.name for file in Path(appdata).iterdir() if file.is_dir()]
            add_host_info(vm_id, hostname, os_name, os_version, mounted_filesystem, cap['docker_installed'], docker_volumes, appdata_folders)
            continue
        elif mounted_filesystem == 'root':
            print(f'Found the Proxmox root filesystem! Collecting host info...')
            vm_id = -999
            hostname = subprocess.check_output(['cat', filesystem_path + '/etc/hostname'], text=True).strip()
            os_release_info = parse_os_release(filesystem_path + '/etc/os-release')
            os_name = os_release_info['ID']
            os_version = os_release_info['VERSION_ID']
            docker = False
            docker_volumes = False
            appdata_folder = False
            add_host_info(vm_id, hostname, os_name, os_version, mounted_filesystem, docker, docker_volumes, appdata_folder)
            continue
        else:
            print(f'Found a vm data volume! Updating host in db...')
            vm_id = int(mounted_filesystem[3:mounted_filesystem.find('-', 3)])
            add_data_volume(vm_id, mounted_filesystem)
            continue

