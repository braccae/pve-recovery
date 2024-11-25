
def mount_lvs(mount_folder_root, devices):
    for device in devices:
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