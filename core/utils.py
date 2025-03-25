"""
Utility functions for Emby FFMPEG Fixer.
Contains pure utility functions with no state management.
"""
import os
import sys
import platform
import shutil
import logging
import subprocess
from datetime import datetime

def setup_logging():
    """Configure logging for the application"""
    logs_dir = 'logs'
    try:
        # Create logs directory with proper permissions
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, mode=0o755, exist_ok=True)
        
        # Ensure the logs directory is writable
        if not os.access(logs_dir, os.W_OK):
            raise OSError(f"Logs directory {logs_dir} is not writable")

        log_file = os.path.join(logs_dir, 'emby_ffmpeg_fixer.log')
        
        # Configure logging with proper file permissions
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Set proper file permissions for the log file
        if os.path.exists(log_file):
            os.chmod(log_file, 0o644)
            
        return True
    except OSError as e:
        print(f"Error setting up logging: {e}")
        return False

def get_system_architecture():
    """Get the system architecture."""
    arch = platform.machine()
    if arch == 'x86_64':
        return 'x86_64'
    elif arch == 'arm64':
        return 'arm64'
    else:
        return arch

def get_default_emby_path():
    """Get the default Emby Server installation path."""
    default_paths = [
        "/Applications/EmbyServer.app",  # macOS
        "/Applications/Emby Server.app",  # macOS alternative
        "C:\\Program Files\\Emby Server",  # Windows
        "/opt/emby-server"  # Linux
    ]
    
    # On macOS, prioritize EmbyServer.app
    if platform.system() == 'Darwin':
        mac_paths = [p for p in default_paths if p.endswith('.app')]
        for path in mac_paths:
            if os.path.exists(path):
                return path
    
    # For other systems or if no macOS path found
    for path in default_paths:
        if os.path.exists(path):
            return path
    return None

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def find_ffmpeg_binaries(emby_path):
    """Find FFMPEG binaries in Emby Server installation."""
    try:
        # macOS paths
        if platform.system() == 'Darwin':
            ffmpeg_path = os.path.join(emby_path, 'Contents', 'Resources', 'ffmpeg')
            if os.path.exists(ffmpeg_path):
                return ffmpeg_path
        # Windows paths
        elif platform.system() == 'Windows':
            ffmpeg_path = os.path.join(emby_path, 'ffmpeg')
            if os.path.exists(ffmpeg_path):
                return ffmpeg_path
        # Linux paths
        else:
            ffmpeg_path = os.path.join(emby_path, 'ffmpeg')
            if os.path.exists(ffmpeg_path):
                return ffmpeg_path
        
        return None
    except Exception as e:
        logging.error(f"Error finding FFMPEG binaries: {e}")
        return None

def get_ffmpeg_architecture(ffmpeg_path):
    """Get the architecture of FFMPEG binary."""
    try:
        result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True)
        if 'arm64' in result.stdout.lower():
            return 'arm64'
        elif 'x86_64' in result.stdout.lower():
            return 'x86_64'
        return None
    except Exception as e:
        logging.error(f"Error getting FFMPEG architecture: {e}")
        return None

def backup_original_ffmpeg(ffmpeg_path):
    """Backup original FFMPEG binary."""
    try:
        backup_path = f"{ffmpeg_path}.backup"
        if not os.path.exists(backup_path):
            shutil.copy2(ffmpeg_path, backup_path)
            return True
        return False
    except Exception as e:
        logging.error(f"Error backing up FFMPEG: {e}")
        return False

def restore_original_ffmpeg(ffmpeg_path):
    """Restore original FFMPEG binary from backup."""
    try:
        backup_path = f"{ffmpeg_path}.backup"
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, ffmpeg_path)
            return True
        return False
    except Exception as e:
        logging.error(f"Error restoring FFMPEG: {e}")
        return False

def replace_ffmpeg_binaries(ffmpeg_path, new_ffmpeg_path):
    """Replace FFMPEG binaries with new ones."""
    try:
        shutil.copy2(new_ffmpeg_path, ffmpeg_path)
        return True
    except Exception as e:
        logging.error(f"Error replacing FFMPEG: {e}")
        return False

def force_single_architecture(ffmpeg_path, target_arch):
    """Force FFMPEG to use single architecture."""
    try:
        if platform.system() == 'Darwin':
            cmd = ['lipo', '-thin', target_arch, ffmpeg_path, '-output', f"{ffmpeg_path}.tmp"]
            subprocess.run(cmd, check=True)
            os.replace(f"{ffmpeg_path}.tmp", ffmpeg_path)
            return True
        return False
    except Exception as e:
        logging.error(f"Error forcing architecture: {e}")
        return False

def create_backup(emby_path):
    """Create a backup of the current Emby Server state."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(os.path.dirname(emby_path), f"emby_backup_{timestamp}")
        shutil.copytree(emby_path, backup_dir)
        return {"success": True, "backup_dir": backup_dir}
    except Exception as e:
        return {"success": False, "message": str(e)}

def restore_from_backup(backup_dir, emby_path):
    """Restore Emby Server from backup."""
    try:
        if os.path.exists(emby_path):
            shutil.rmtree(emby_path)
        shutil.copytree(backup_dir, emby_path)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}

def force_architecture_incompatibility(ffmpeg_path):
    """Force FFMPEG to use incompatible architecture."""
    try:
        if platform.system() == 'Darwin':
            current_arch = get_ffmpeg_architecture(ffmpeg_path)
            if current_arch == 'arm64':
                return force_single_architecture(ffmpeg_path, 'x86_64')
            else:
                return force_single_architecture(ffmpeg_path, 'arm64')
        return False
    except Exception as e:
        logging.error(f"Error forcing architecture incompatibility: {e}")
        return False

def create_initial_state_backup(emby_path):
    """Create a backup of the initial Emby Server state."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(os.path.dirname(emby_path), f"emby_initial_backup_{timestamp}")
        shutil.copytree(emby_path, backup_dir)
        return {"success": True, "backup_dir": backup_dir}
    except Exception as e:
        return {"success": False, "message": str(e)}

def restore_initial_state(emby_path):
    """Restore Emby Server to initial state."""
    try:
        backup_dir = state_manager.get_initial_state_backup_dir()
        if not backup_dir or not os.path.exists(backup_dir):
            return {"success": False, "message": "No initial state backup found"}
        
        if os.path.exists(emby_path):
            shutil.rmtree(emby_path)
        shutil.copytree(backup_dir, emby_path)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)} 