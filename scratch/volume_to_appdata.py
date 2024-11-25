import os
import subprocess
import pathlib
from pathlib import Path
import tarfile
import glob

## functions
def create_tar_archive(source_dir, output_path, new_parent_name=None):
    """
    Create a tar archive of a directory while preserving permissions and attributes.
    Optionally replace the parent directory name in the archive.
    
    Args:
        source_dir: Path to the directory to archive
        output_path: Path where to save the tar file
        new_parent_name: If provided, replace the source directory name with this name
    """
    with tarfile.open(output_path, "w:gz") as tar:
        original_dir = os.getcwd()
        os.chdir(os.path.dirname(source_dir))
        source_basename = os.path.basename(source_dir)
        
        try:
            def custom_filter(tarinfo):
                # Preserve all attributes
                if new_parent_name:
                    # Replace the top-level directory name
                    tarinfo.name = tarinfo.name.replace(source_basename, new_parent_name, 1)
                return tarinfo
                
            tar.add(source_basename, 
                   recursive=True,
                   filter=custom_filter)
        finally:
            os.chdir(original_dir)

def merge_tar_archives(input_archives, output_archive):
    """
    Merge multiple .tar.gz archives into a single archive while preserving structure and permissions.
    
    Args:
        input_archives: List of paths to input .tar.gz files
        output_archive: Path where the merged archive will be saved
    """
    # Create a temporary directory to extract files
    with tarfile.open(output_archive, 'w:gz') as output_tar:
        # Process each input archive
        for archive_path in input_archives:
            with tarfile.open(archive_path, 'r:gz') as input_tar:
                for member in input_tar.getmembers():
                    # Extract file content to memory
                    if member.isfile():
                        member_file = input_tar.extractfile(member)
                        if member_file:  # Skip if None (for symlinks etc)
                            # Add the file to the new archive with original info
                            output_tar.addfile(member, member_file)
                    else:
                        # For directories and other special files, just add the member
                        output_tar.addfile(member)


def backup_and_migrate_volumes(stackname, volumes_dir, output_dir=os.getcwd()):
    volumes_data = []
    volumes_dir = Path(volumes_dir)
    for volume in volumes_dir.iterdir():
        volume_name = os.path.basename(volume)
        volume_root = pathlib.Path(volume)
        stackname_suffix = stackname + '_'
        volume_data_name = volume_name.replace(stackname_suffix, '')
        volume_data_root = volume_root / '_data'
        valid_data_volume = volume_data_root.exists()
        output_file = f'{stackname_suffix}{volume_data_name}.tar.gz'
        if output_dir is not None:
            output_dir_path = Path(output_dir)
            output = Path(output_dir_path / output_file)
        if not valid_data_volume:
            print(f'No data found in volume: {volume}')
        else:
            #print(f'Found data in volume: {volume}! Volume name: {volume_name} Volume data root: {volume_data_root} Appdata name: {volume_data_name}')
            new_parent_name = f'{stackname_suffix.rstrip("_")}/{volume_data_name}'
            print(f'Proccessing {volume_data_name} with new parent dir of {new_parent_name}')
            create_tar_archive(volume_data_root, output, new_parent_name)
            print(f'Finished creating tar archive: {output_file} from volume: {volume}')
    print(f'Finished processing volumes. Merging tar archives...')

    merge_tar_archives(list(output_dir_path.glob('*.tar.gz')), stackname_suffix.rstrip("_") + '.tar.gz')

## RUN

stackname = 'auth-stack'
volumes_dir = 'auth_root/var/lib/docker/volumes'
temp_dir = 'auth_appdata'

backup_and_migrate_volumes(stackname, volumes_dir, temp_dir)