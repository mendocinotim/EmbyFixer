import os
import sys
import platform
import shutil
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(filename='emby_ffmpeg_fixer.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_system_architecture():
    """Detect system architecture (x86_64 or arm64)"""
    arch = platform.machine()
    if arch == "x86_64" or arch == "AMD64" or arch == "i386":
        return "x86_64"
    elif arch == "arm64" or arch == "aarch64":
        return "arm64"
    else:
        return arch

def find_ffmpeg_binaries(emby_path):
    """Find FFMPEG binaries within Emby Server application"""
    if not emby_path or not os.path.exists(emby_path):
        return None
    
    # For macOS, search within the app bundle
    if emby_path.endswith(".app"):
        search_paths = [
            os.path.join(emby_path, "Contents", "MacOS", "ffmpeg"),
            os.path.join(emby_path, "Contents", "Resources", "ffmpeg")
        ]
        
        # Search for a directory containing FFMPEG binaries
        for path in search_paths:
            if os.path.exists(path):
                return path
            
        # If directory not found, search for the binaries directly
        for root, dirs, files in os.walk(emby_path):
            if "ffmpeg" in files:
                return root
    
    return None

def get_ffmpeg_architecture(ffmpeg_path):
    """Determine architecture of FFMPEG binary"""
    if not ffmpeg_path or not os.path.exists(ffmpeg_path):
        return None
    
    try:
        ffmpeg_bin = os.path.join(ffmpeg_path, "ffmpeg")
        if not os.path.exists(ffmpeg_bin):
            return None
        
        # Run file command to check architecture
        result = subprocess.run(["file", ffmpeg_bin], capture_output=True, text=True)
        output = result.stdout.lower()
        
        if "x86_64" in output:
            return "x86_64"
        elif "arm64" in output:
            return "arm64"
        else:
            return "unknown"
    except Exception as e:
        logging.error(f"Error determining FFMPEG architecture: {e}")
        return None

def backup_original_ffmpeg(ffmpeg_path):
    """Backup original FFMPEG binaries before replacing"""
    if not ffmpeg_path or not os.path.exists(ffmpeg_path):
        return False

    try:
        # Create backup directory using timestamp
        backup_dir = os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_backup_original")
        
        # If backup already exists, don't overwrite it
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
            # Copy all files from ffmpeg directory to backup
            for file_name in os.listdir(ffmpeg_path):
                src_file = os.path.join(ffmpeg_path, file_name)
                if os.path.isfile(src_file):
                    dest_file = os.path.join(backup_dir, file_name)
                    shutil.copy2(src_file, dest_file)
                    logging.info(f"Backed up {file_name} to {backup_dir}")
            
            return True
        else:
            logging.info(f"Backup already exists at {backup_dir}")
            return True
    except Exception as e:
        logging.error(f"Error backing up FFMPEG: {e}")
        return False

def restore_original_ffmpeg(emby_path):
    """Restore original FFMPEG binaries from backup"""
    if not emby_path or not os.path.exists(emby_path):
        return False, "Invalid Emby Server path"
    
    ffmpeg_path = find_ffmpeg_binaries(emby_path)
    if not ffmpeg_path:
        return False, "FFMPEG binaries not found in Emby Server"
    
    backup_dir = os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_backup_original")
    if not os.path.exists(backup_dir):
        return False, "No backup found to restore"
    
    try:
        # Copy all files from backup to ffmpeg directory
        for file_name in os.listdir(backup_dir):
            src_file = os.path.join(backup_dir, file_name)
            if os.path.isfile(src_file):
                dest_file = os.path.join(ffmpeg_path, file_name)
                shutil.copy2(src_file, dest_file)
                logging.info(f"Restored {file_name} to {ffmpeg_path}")
        
        return True, "Original FFMPEG binaries restored successfully"
    except Exception as e:
        logging.error(f"Error restoring FFMPEG: {e}")
        return False, f"Error restoring FFMPEG: {str(e)}"

def replace_ffmpeg_binaries(emby_path, system_arch):
    """Replace FFMPEG binaries with correct architecture"""
    if not emby_path or not os.path.exists(emby_path):
        return False, "Invalid Emby Server path"
    
    ffmpeg_path = find_ffmpeg_binaries(emby_path)
    if not ffmpeg_path:
        return False, "FFMPEG binaries not found in Emby Server"
    
    # Backup original before replacing
    if not backup_original_ffmpeg(ffmpeg_path):
        return False, "Failed to backup original FFMPEG binaries"
    
    try:
        # Get path to replacement binaries
        replacement_path = get_resource_path(f"ffmpeg_binaries/{system_arch}")
        if not os.path.exists(replacement_path):
            return False, f"Replacement FFMPEG binaries for {system_arch} not found"
        
        # Copy replacement binaries to Emby
        for file_name in os.listdir(replacement_path):
            src_file = os.path.join(replacement_path, file_name)
            if os.path.isfile(src_file):
                dest_file = os.path.join(ffmpeg_path, file_name)
                shutil.copy2(src_file, dest_file)
                # Make executable
                os.chmod(dest_file, 0o755)
                logging.info(f"Replaced {file_name} with {system_arch} version")
        
        return True, f"FFMPEG binaries replaced with {system_arch} versions"
    except Exception as e:
        logging.error(f"Error replacing FFMPEG: {e}")
        return False, f"Error replacing FFMPEG: {str(e)}"
