import os
import pathlib
from pathlib import Path
import subprocess
import sqlite3
import csv
import time

## initialize
current_dir = Path.cwd()
print(f'current_dir: {current_dir}')
# db
conn = sqlite3.connect('pve_recovery.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS devices (
        device TEXT PRIMARY KEY,
        vm_id INTEGER,
        path TEXT,
        fs_type TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS hosts (
        vm_id INTEGER PRIMARY KEY,
        hostname TEXT,
        os_name TEXT,
        os_version TEXT,
        root_volume TEXT,
        data_volumes TEXT,
        docker BOOLEAN,
        volumes TEXT,
        appdata TEXT
    )
''')
os.chmod('pve_recovery.db', 0o777)
## Functions
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

def check_appdata_folder(root_folder):
    """Checks if the appdata folder exists."""
    appdata_folder = os.path.join(root_folder, '/mnt/user/appdata')
    return os.path.exists(appdata_folder)

# db stuff
def add_new_device(device, device_path, fs_type, vm_id):
    """Adds a new device to the database."""
    if cursor.execute('SELECT * FROM devices WHERE device = ?', (device,)).fetchone() is not None:
        cursor.execute('''
            UPDATE devices
            SET path = ?, fs_type = ?, vm_id = ?
            WHERE device = ?
        ''', (device, device_path, fs_type, vm_id))
    else:   cursor.execute('''
            INSERT INTO devices (device, path, fs_type, vm_id)
            VALUES (?, ?, ?, ?)
        ''', (device, device_path, fs_type, vm_id))
    conn.commit() 
    time.sleep(0.5)
    return

def add_host_info(vm_id, hostname, os_name, os_version, root_volume, docker, docker_volumes, appdata_folder):
    """Adds a new host to the database."""
    if cursor.execute('SELECT * FROM hosts WHERE vm_id = ?', (vm_id,)).fetchone() is not None:
        print(f'updated host info for vm {vm_id}, updating...')
        cursor.execute('''
            UPDATE hosts
            SET hostname = ?, os_name = ?, os_version = ?, root_volume = ?, docker = ?, docker_volumes = ?, appdata_folder = ?
            WHERE vm_id = ?
        ''', (hostname, os_name, os_version, root_volume, docker, docker_volumes, appdata_folder, vm_id))
    else:
        print(f'new host info for vm {vm_id}, adding...')
        cursor.execute('''
            INSERT INTO hosts (vm_id, hostname, os_name, os_version, root_volume docker docker_volumes appdata_folder)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (vm_id, hostname, os_name, os_version, root_volume, docker, docker_volumes, appdata_folder))
    conn.commit() 
    time.sleep(0.5)
    return

def add_data_volume(vm_id, new_volume):
    """Adds a data volume to a VM's record, creating the VM record if it doesn't exist.
    
    Args:
        vm_id: The ID of the VM
        new_volume: The volume name to add
    """
    # Check if VM exists
    vm_exists = cursor.execute('SELECT data_volumes FROM hosts WHERE vm_id = ?', (vm_id,)).fetchone()
    
    if vm_exists is None:
        # VM doesn't exist, create new record
        cursor.execute('''
            INSERT INTO hosts (vm_id, data_volumes)
            VALUES (?, ?)
        ''', (vm_id, new_volume))
    else:
        # VM exists, check and update volumes
        data_volumes = vm_exists[0]
        if data_volumes is None or data_volumes == '':
            # No volumes yet
            updated_volumes = new_volume
        else:
            # Check if volume already exists
            existing_volumes = data_volumes.split(',')
            if new_volume not in existing_volumes:
                updated_volumes = data_volumes + ',' + new_volume
            else:
                print(f'Volume {new_volume} already recorded for VM {vm_id}')
                return
        
        # Update the record
        cursor.execute('''
            UPDATE hosts
            SET data_volumes = ?
            WHERE vm_id = ?
        ''', (updated_volumes, vm_id))
    
    conn.commit()
    time.sleep(1)
    return
##


pve_device_folder = Path('/dev/pve')
pve_devices_unsorted = [file.name for file in pve_device_folder.iterdir() if file.is_block_device()]
pve_devices = sorted(pve_devices_unsorted)
mount_folder_root = '/mnt/pve'


print('now printing all found pve devices')


for pve_device in pve_devices:
    pve_device_path = str(pve_device_folder) + '/' + pve_device
    fs_type = get_fs_type(pve_device_path)
    vm_id = -1
    # Unmount the device if it's mounted
    subprocess.run(['umount', pve_device_path])

    if pve_device.startswith('vm-'):
        vm_id = int(pve_device[3:pve_device.find('-', 3)])
    add_new_device(pve_device, pve_device_path, fs_type, vm_id)
    print(f'Added new device to database!: id: {vm_id} device: {pve_device} type: {fs_type} path: {pve_device_path}')

    if fs_type is not None and fs_type != 'Unknown' and fs_type != 'swap':
        print(f'found identified pve volume: {pve_device} type: {fs_type}')
        
        mountpoint = mount_folder_root + '/' + pve_device
        print(f'creating mountpoint at {mountpoint}')
        try:
            Path(mountpoint).mkdir(parents=True, exist_ok=True)
            print(f'successfully created mountpoint!')
        except Exception as e:
            print(f'error creating mountpoint at {mountpoint}. Are you root?: {e}')
        
        print(f'attempting to mount {pve_device} at {mountpoint}')
        try:
            subprocess.run(['mount', pve_device_path, mountpoint, '-o', 'ro'])
            print(f'successfully mounted {pve_device}')
        except Exception as e:
            print(f'error mounting {pve_device}: {e}')
    else:
        print(f'{pve_device} is not mountable! type: {fs_type}')
        continue
    


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