import sqlite3 

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
os.chmod('pve_recovery.db', 0o777)# db stuff


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