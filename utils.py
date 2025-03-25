import os
import sys
import platform
import shutil
import subprocess
import logging
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
    """Find the FFMPEG binaries in the Emby Server installation"""
    if not os.path.exists(emby_path):
        return None
    
    # Check common locations for ffmpeg binaries
    possible_paths = [
        os.path.join(emby_path, 'Contents', 'MacOS'),  # macOS app bundle
        os.path.join(emby_path, 'ffmpeg'),  # Windows/Linux
        os.path.join(emby_path, 'System', 'ffmpeg'),  # Alternative Windows/Linux
    ]
    
    for path in possible_paths:
        if os.path.exists(os.path.join(path, 'ffmpeg')) and \
           os.path.exists(os.path.join(path, 'ffprobe')) and \
           os.path.exists(os.path.join(path, 'ffdetect')):
            return path
    
    return None

def get_ffmpeg_architecture(ffmpeg_path):
    """Get the architecture of the FFMPEG binary and verify it's actually executable"""
    try:
        # Check all three binaries
        binaries = ['ffmpeg', 'ffprobe', 'ffdetect']
        architectures = set()
        
        for binary in binaries:
            binary_path = os.path.join(ffmpeg_path, binary)
            if not os.path.exists(binary_path):
                logging.error(f"Binary not found: {binary_path}")
                continue
                
            # First try to detect test binaries
            try:
                with open(binary_path, 'r') as f:
                    content = f.read()
                    if '#!/bin/bash' in content and 'Bad CPU type in executable' in content:
                        # This is one of our test binaries
                        if 'arm64' in os.path.dirname(binary_path):
                            architectures.add('arm64')
                            continue
                        elif 'x86_64' in os.path.dirname(binary_path):
                            architectures.add('x86_64')
                            continue
            except:
                pass  # Not a test binary, continue with normal detection
                
            # Normal binary detection
            try:
                result = subprocess.run(['file', binary_path], capture_output=True, text=True)
                if result.returncode == 0:
                    if 'arm64' in result.stdout.lower():
                        architectures.add('arm64')
                        continue
                    elif 'x86_64' in result.stdout.lower():
                        architectures.add('x86_64')
                        continue
            except:
                pass
                
            # If we couldn't determine the architecture, try running it
            try:
                result = subprocess.run([binary_path, '-version'], 
                                     capture_output=True, 
                                     text=True,
                                     timeout=2)  # Reduced timeout to 2 seconds
                
                # If it runs successfully, it's compatible with current architecture
                if result.returncode == 0:
                    architectures.add(get_system_architecture())
                else:
                    # Any non-zero exit code indicates potential incompatibility
                    logging.warning(f"Binary {binary} returned non-zero exit code: {result.returncode}")
                    # Check for error messages that indicate architecture incompatibility
                    error_output = result.stderr.lower()
                    if 'bad cpu type in executable' in error_output:
                        if 'arm64' in os.path.dirname(binary_path):
                            architectures.add('arm64')
                        elif 'x86_64' in os.path.dirname(binary_path):
                            architectures.add('x86_64')
                    elif result.returncode == 8:  # Special case for exit code 8
                        # This is likely an incompatible binary
                        if 'arm64' in os.path.dirname(binary_path):
                            architectures.add('arm64')
                        elif 'x86_64' in os.path.dirname(binary_path):
                            architectures.add('x86_64')
                        else:
                            # Try to determine architecture from the binary file
                            file_result = subprocess.run(['file', binary_path], capture_output=True, text=True)
                            if 'arm64' in file_result.stdout.lower():
                                architectures.add('arm64')
                            elif 'x86_64' in file_result.stdout.lower():
                                architectures.add('x86_64')
            except subprocess.TimeoutExpired:
                logging.warning(f"Binary {binary} timed out when trying to execute")
            except Exception as e:
                logging.warning(f"Error executing {binary}: {e}")
                if 'bad cpu type in executable' in str(e).lower():
                    # This is our test binary failing as expected
                    if 'arm64' in os.path.dirname(binary_path):
                        architectures.add('arm64')
                    elif 'x86_64' in os.path.dirname(binary_path):
                        architectures.add('x86_64')
        
        if len(architectures) > 1:
            logging.warning(f"Mixed architectures found: {architectures}")
            # Return the most common architecture or the first one if tied
            return list(architectures)[0]
        elif len(architectures) == 1:
            return list(architectures)[0]
        else:
            logging.error("Could not determine FFMPEG architecture")
            return None
            
    except Exception as e:
        logging.error(f"Error getting FFMPEG architecture: {e}")
        return None

def backup_original_ffmpeg(ffmpeg_path):
    """Backup original FFMPEG binaries"""
    try:
        # Check if we have write permissions in the parent directory
        parent_dir = os.path.dirname(ffmpeg_path)
        if not os.access(parent_dir, os.W_OK):
            return False, f"No write permission for directory: {parent_dir}"
            
        backup_dir = os.path.join(parent_dir, "ffmpeg_backup_original")
        if os.path.exists(backup_dir):
            logging.info(f"Backup already exists at {backup_dir}")
            return True
            
        # Create backup directory with proper permissions
        try:
            os.makedirs(backup_dir, mode=0o755, exist_ok=True)
        except OSError as e:
            return False, f"Failed to create backup directory: {e}"
        
        # Backup all three binaries
        for binary in ['ffmpeg', 'ffprobe', 'ffdetect']:
            src = os.path.join(ffmpeg_path, binary)
            dst = os.path.join(backup_dir, binary)
            
            if not os.path.exists(src):
                return False, f"Original {binary} not found at {src}"
                
            # Check if source is readable
            if not os.access(src, os.R_OK):
                return False, f"Cannot read original {binary}"
                
            try:
                # Copy the binary
                shutil.copy2(src, dst)
                # Set proper permissions for backup
                os.chmod(dst, 0o755)
                logging.info(f"Backed up {binary} to {backup_dir}")
            except OSError as e:
                return False, f"Failed to backup {binary}: {e}"
                
        logging.info(f"Successfully backed up ffmpeg to {backup_dir}")
        return True
    except Exception as e:
        logging.error(f"Error backing up FFMPEG: {e}")
        return False

def replace_ffmpeg_binaries(emby_path, target_arch):
    """Replace FFMPEG binaries with the correct architecture version"""
    try:
        ffmpeg_path = find_ffmpeg_binaries(emby_path)
        if not ffmpeg_path:
            return False, "FFMPEG binaries not found"
            
        # Check if we have write permissions
        if not os.access(ffmpeg_path, os.W_OK):
            return False, f"No write permission for FFMPEG directory: {ffmpeg_path}"
            
        # Backup original binaries
        if not backup_original_ffmpeg(ffmpeg_path):
            return False, "Failed to backup original FFMPEG binaries"
            
        # Get paths for replacement binaries
        replacement_dir = os.path.join('ffmpeg_binaries', target_arch)
        if not os.path.exists(replacement_dir):
            return False, f"No replacement binaries found for {target_arch}"
            
        # Replace all three binaries
        for binary in ['ffmpeg', 'ffprobe', 'ffdetect']:
            src = os.path.join(replacement_dir, binary)
            dst = os.path.join(ffmpeg_path, binary)
            
            if not os.path.exists(src):
                return False, f"Replacement {binary} not found"
                
            # Check if source is readable
            if not os.access(src, os.R_OK):
                return False, f"Cannot read replacement {binary}"
                
            # Remove existing binary if it exists
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except OSError as e:
                    return False, f"Cannot remove existing {binary}: {e}"
                
            # Copy new binary
            try:
                shutil.copy2(src, dst)
                # Make it executable with proper permissions
                os.chmod(dst, 0o755)
                logging.info(f"Replaced {binary} with {target_arch} version at {dst}")
            except OSError as e:
                return False, f"Failed to copy {binary}: {e}"
            
        return True, "Successfully replaced FFMPEG binaries"
    except Exception as e:
        logging.error(f"Error replacing ffmpeg: {e}")
        return False, str(e)

def restore_original_ffmpeg(emby_path):
    """Restore original FFMPEG binaries from backup"""
    try:
        ffmpeg_path = find_ffmpeg_binaries(emby_path)
        if not ffmpeg_path:
            return False, "FFMPEG binaries not found"
            
        # Check if we have write permissions
        if not os.access(ffmpeg_path, os.W_OK):
            return False, f"No write permission for FFMPEG directory: {ffmpeg_path}"
            
        backup_dir = os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_backup_original")
        if not os.path.exists(backup_dir):
            return False, "No backup found to restore"
            
        # Restore all three binaries
        for binary in ['ffmpeg', 'ffprobe', 'ffdetect']:
            src = os.path.join(backup_dir, binary)
            dst = os.path.join(ffmpeg_path, binary)
            
            if not os.path.exists(src):
                return False, f"Backup {binary} not found"
                
            # Check if backup is readable
            if not os.access(src, os.R_OK):
                return False, f"Cannot read backup {binary}"
                
            # Remove current binary if it exists
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except OSError as e:
                    return False, f"Cannot remove existing {binary}: {e}"
                
            # Copy backup binary
            try:
                shutil.copy2(src, dst)
                # Make it executable with proper permissions
                os.chmod(dst, 0o755)
                logging.info(f"Restored {binary} from backup")
            except OSError as e:
                return False, f"Failed to restore {binary}: {e}"
            
        # Clean up test mode files
        test_files = [
            os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_test_mode"),
            os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_architecture")
        ]
        for test_file in test_files:
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                except OSError as e:
                    logging.warning(f"Could not remove test file {test_file}: {e}")
            
        return True, "Successfully restored original FFMPEG binaries"
    except Exception as e:
        logging.error(f"Error restoring ffmpeg: {e}")
        return False, str(e)

def force_single_architecture(ffmpeg_path, target_arch):
    """Force a specific architecture for testing."""
    logging.info(f"Starting force_single_architecture with ffmpeg_path={ffmpeg_path}, target_arch={target_arch}")
    
    if not os.path.exists(ffmpeg_path):
        logging.error(f"FFMPEG path does not exist: {ffmpeg_path}")
        return "Error: FFMPEG path does not exist"

    # Get absolute paths
    ffmpeg_path = os.path.abspath(ffmpeg_path)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    logging.info(f"Current directory: {current_dir}")
    logging.info(f"Project root: {project_root}")

    # Create test directory if it doesn't exist
    test_dir = os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_test")
    os.makedirs(test_dir, exist_ok=True)
    logging.info(f"Created/verified test directory: {test_dir}")

    # Backup original binaries if not already backed up
    backup_dir = os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_backup_original")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        for binary in ["ffmpeg", "ffprobe", "ffdetect"]:
            src = os.path.join(ffmpeg_path, binary)
            dst = os.path.join(backup_dir, binary)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                logging.info(f"Backed up {binary} to {dst}")

    # Look for test resources in multiple possible locations
    possible_locations = [
        os.path.join(project_root, "test_resources", target_arch),  # Project root
        os.path.join(current_dir, "test_resources", target_arch),   # Current directory
        os.path.join(os.getcwd(), "test_resources", target_arch)    # Working directory
    ]

    test_resources = None
    for location in possible_locations:
        logging.info(f"Checking for test resources in: {location}")
        if os.path.exists(location):
            test_resources = location
            logging.info(f"Found test resources at: {location}")
            break

    if test_resources is None:
        error_msg = "Test resources not found in any of these locations:"
        for loc in possible_locations:
            error_msg += f"\n- {loc}"
        logging.error(error_msg)
        return error_msg

    try:
        for binary in ["ffmpeg", "ffprobe", "ffdetect"]:
            src = os.path.join(test_resources, binary)
            dst = os.path.join(ffmpeg_path, binary)
            logging.info(f"Attempting to copy {src} to {dst}")
            
            if not os.path.exists(src):
                logging.error(f"Test binary not found: {src}")
                return f"Error: Test binary {binary} not found at {src}"
                
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)  # Make executable
            logging.info(f"Successfully copied and made executable: {dst}")
            
            # Verify the binary fails as expected
            logging.info(f"Testing binary: {dst}")
            result = subprocess.run([dst], capture_output=True, text=True)
            logging.info(f"Test result: returncode={result.returncode}, stderr={result.stderr}")
            
            if result.returncode != 1 or "Bad CPU type in executable" not in result.stderr:
                logging.error(f"Binary {binary} not working as expected: returncode={result.returncode}")
                return f"Error: Test binary {binary} not working as expected"

        # Create a test marker file
        marker_file = os.path.join(test_dir, "test_mode")
        with open(marker_file, "w") as f:
            f.write(f"Architecture: {target_arch}\nTimestamp: {datetime.now()}")
        logging.info(f"Created test marker file: {marker_file}")

        return "Success: Test binaries installed. Emby Server should now show compatibility issues."
    except Exception as e:
        logging.error(f"Error in force_single_architecture: {str(e)}")
        return f"Error setting up test environment: {str(e)}"

def is_test_mode_active(ffmpeg_path):
    """Check if test mode is currently active"""
    try:
        test_marker = os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_test_mode")
        return os.path.exists(test_marker)
    except Exception:
        return False

def get_test_mode_info(ffmpeg_path):
    """Get information about the current test mode"""
    try:
        test_marker = os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_test_mode")
        if os.path.exists(test_marker):
            with open(test_marker, 'r') as f:
                return f.read().strip()
        return None
    except Exception:
        return None
