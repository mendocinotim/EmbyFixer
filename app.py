from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
from waitress import serve
import os
import sys
import platform
import subprocess
import logging
import psutil
import signal
from datetime import datetime
from utils import (
    get_system_architecture, 
    find_ffmpeg_binaries,
    get_ffmpeg_architecture,
    backup_original_ffmpeg,
    restore_original_ffmpeg,
    replace_ffmpeg_binaries,
    force_single_architecture,
    setup_logging,
    get_test_mode_info,
    is_test_mode_active
)

# Global Configuration
APP_PORT = 5004  # Application port number

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['EMBY_PATH'] = None  # Initialize EMBY_PATH config
app.config['DEBUG'] = False  # Disable debug mode
app.config['PROPAGATE_EXCEPTIONS'] = True  # Enable exception propagation
app.config['MAIN_APP_RUNNING'] = False  # Track if main app is running

# Configure logging
setup_logging()

def kill_existing_flask():
    """Kill any existing Flask processes running on port APP_PORT"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'python' in cmdline[0] and 'app.py' in ' '.join(cmdline):
                    if proc.pid != os.getpid():  # Don't kill ourselves
                        proc.kill()
                        logging.info(f"Killed existing Flask process: {proc.pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logging.error(f"Error killing existing Flask processes: {e}")

def is_port_in_use(port):
    """Check if a port is in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

@app.route('/')
def index():
    """Show start page if main app is not running, otherwise redirect to main"""
    if app.config['MAIN_APP_RUNNING']:
        return redirect(url_for('main'))
    return render_template('start.html')

@app.route('/main')
def main():
    """Main application page"""
    if not app.config['MAIN_APP_RUNNING']:
        return redirect(url_for('index'))
    # Pre-populate the Emby Server path
    default_path = '/Applications/EmbyServer.app'
    return render_template('index.html', default_emby_path=default_path)

@app.route('/api/start-application', methods=['POST'])
def start_application():
    """Start the main application"""
    try:
        logging.info("Attempting to start main application")
        
        # Check if another instance is running
        if is_port_in_use(APP_PORT):
            logging.info("Found existing Flask process, attempting to kill it")
            kill_existing_flask()
            # Give the process a moment to terminate
            import time
            time.sleep(1)
        
        # Start the main application
        app.config['MAIN_APP_RUNNING'] = True
        logging.info("Main application started successfully")
        
        return jsonify({
            'success': True,
            'message': 'Application started successfully'
        })
    except Exception as e:
        error_msg = f"Error starting application: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

@app.route('/api/select-emby', methods=['POST'])
def select_emby():
    try:
        emby_path = request.json.get('path')
        
        if not emby_path or not os.path.exists(emby_path):
            return jsonify({
                'success': False,
                'message': 'Invalid Emby Server path'
            })
            
        # Check if we have read access to the path
        if not os.access(emby_path, os.R_OK):
            return jsonify({
                'success': False,
                'message': f'No read permission for path: {emby_path}'
            })
        
        # Save the selected path for later use
        app.config['EMBY_PATH'] = emby_path
        
        return jsonify({
            'success': True,
            'path': emby_path
        })
    except Exception as e:
        error_msg = f"Error selecting Emby path: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

@app.route('/api/check-compatibility', methods=['POST'])
def check_compatibility():
    emby_path = request.json.get('path')
    
    if not emby_path or not os.path.exists(emby_path):
        return jsonify({
            'success': False,
            'message': 'Invalid Emby Server path'
        })
    
    # Save the selected path for later use
    app.config['EMBY_PATH'] = emby_path
    
    # Get system architecture
    system_arch = get_system_architecture()
    
    # Find FFMPEG binaries in Emby Server
    ffmpeg_path = find_ffmpeg_binaries(emby_path)
    if not ffmpeg_path:
        return jsonify({
            'success': False,
            'message': 'FFMPEG binaries not found in Emby Server',
            'system_architecture': system_arch
        })
    
    # Get FFMPEG architecture
    ffmpeg_arch = get_ffmpeg_architecture(ffmpeg_path)
    
    # Check compatibility
    is_compatible = (system_arch == ffmpeg_arch)
    
    return jsonify({
        'success': True,
        'system_architecture': system_arch,
        'ffmpeg_architecture': ffmpeg_arch,
        'is_compatible': is_compatible
    })

@app.route('/api/fix-ffmpeg', methods=['POST'])
def fix_ffmpeg():
    emby_path = request.json.get('path')
    
    if not emby_path or not os.path.exists(emby_path):
        return jsonify({
            'success': False,
            'message': 'Invalid Emby Server path'
        })
    
    # Get system architecture
    system_arch = get_system_architecture()
    
    # Replace FFMPEG binaries
    success, message = replace_ffmpeg_binaries(emby_path, system_arch)
    
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/restore-ffmpeg', methods=['POST'])
def restore_ffmpeg():
    """Restore original FFMPEG binaries and clean up test mode"""
    try:
        emby_path = request.json.get('path')
        
        if not emby_path or not os.path.exists(emby_path):
            return jsonify({
                'success': False,
                'message': 'Invalid Emby Server path'
            })
        
        # Restore original FFMPEG binaries
        success, message = restore_original_ffmpeg(emby_path)
        
        if success:
            # Clean up test mode marker if it exists
            test_marker = os.path.join(os.path.dirname(find_ffmpeg_binaries(emby_path)), "ffmpeg_test_mode")
            if os.path.exists(test_marker):
                try:
                    os.remove(test_marker)
                except OSError as e:
                    logging.warning(f"Could not remove test marker file: {e}")
            
            return jsonify({
                'success': True,
                'message': message,
                'details': {
                    'test_mode_cleaned': True,
                    'system_architecture': get_system_architecture(),
                    'ffmpeg_architecture': get_ffmpeg_architecture(find_ffmpeg_binaries(emby_path))
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })
            
    except Exception as e:
        error_msg = f"Error restoring FFMPEG: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

@app.route('/api/check-backup', methods=['POST'])
def check_backup():
    emby_path = request.json.get('path')
    
    if not emby_path or not os.path.exists(emby_path):
        return jsonify({
            'success': False,
            'message': 'Invalid Emby Server path',
            'has_backup': False
        })
    
    ffmpeg_path = find_ffmpeg_binaries(emby_path)
    if not ffmpeg_path:
        return jsonify({
            'success': False,
            'message': 'FFMPEG binaries not found in Emby Server',
            'has_backup': False
        })
    
    backup_dir = os.path.join(os.path.dirname(ffmpeg_path), "ffmpeg_backup_original")
    has_backup = os.path.exists(backup_dir)
    
    return jsonify({
        'success': True,
        'has_backup': has_backup
    })

@app.route('/api/get-logs', methods=['GET', 'OPTIONS'])
def get_logs():
    """Get the contents of the log file"""
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Accept')
        return response

    try:
        log_file = os.path.join('logs', 'emby_ffmpeg_fixer.log')
        logging.info(f"Attempting to read log file: {log_file}")
        
        if not os.path.exists(log_file):
            logging.error(f"Log file not found: {log_file}")
            response = jsonify({
                'success': False,
                'message': 'Log file not found'
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404

        logging.info("Reading log file contents")
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.read()
            logging.info(f"Successfully read {len(logs)} bytes from log file")

        # Return logs with proper headers
        response = jsonify({
            'success': True,
            'logs': logs
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Accept')
        response.headers.add('Content-Type', 'application/json')
        logging.info("Returning log file contents with CORS headers")
        return response

    except Exception as e:
        logging.error(f"Error reading logs: {str(e)}", exc_info=True)
        response = jsonify({
            'success': False,
            'message': f'Error reading logs: {str(e)}'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/download-log')
def download_log():
    log_file = os.path.join('logs', 'emby_ffmpeg_fixer.log')
    return send_file(log_file, as_attachment=True)

@app.route('/api/force-test-mode', methods=['POST'])
def force_test_mode():
    """Force FFMPEG binaries to be single-architecture for testing"""
    try:
        emby_path = request.json.get('path')
        target_arch = request.json.get('architecture')  # 'x86_64' or 'arm64'
        
        if not emby_path or not os.path.exists(emby_path):
            return jsonify({
                'success': False,
                'message': 'Invalid Emby Server path'
            })
        
        if target_arch not in ['x86_64', 'arm64']:
            return jsonify({
                'success': False,
                'message': 'Invalid architecture specified'
            })
        
        # Get current system architecture
        system_arch = get_system_architecture()
        
        # Only allow forcing incompatible architecture
        if target_arch == system_arch:
            return jsonify({
                'success': False,
                'message': f'Cannot force {target_arch} architecture as it matches your system. Please select the opposite architecture to simulate incompatibility.'
            })
        
        # Force single architecture
        message = force_single_architecture(find_ffmpeg_binaries(emby_path), target_arch)
        success = message.startswith('Success:')
        
        if success:
            # Get test mode info
            test_info = get_test_mode_info(emby_path)
            
            return jsonify({
                'success': True,
                'message': message,
                'test_info': test_info,
                'details': {
                    'system_architecture': system_arch,
                    'forced_architecture': target_arch,
                    'emby_path': emby_path,
                    'warning': 'Emby Server should now show compatibility issues. Use the Fix button to resolve them.'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })
            
    except Exception as e:
        error_msg = f"Error setting up test mode: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

@app.route('/api/check-test-mode', methods=['POST'])
def check_test_mode():
    """Check if test mode is currently active and get its status"""
    try:
        emby_path = request.json.get('path')
        
        if not emby_path or not os.path.exists(emby_path):
            return jsonify({
                'success': False,
                'message': 'Invalid Emby Server path',
                'test_mode_active': False
            })
        
        # Check if test mode is active
        is_active = is_test_mode_active(emby_path)
        test_info = get_test_mode_info(emby_path) if is_active else None
        
        # Get current FFMPEG architecture
        ffmpeg_path = find_ffmpeg_binaries(emby_path)
        current_arch = get_ffmpeg_architecture(ffmpeg_path) if ffmpeg_path else None
        system_arch = get_system_architecture()
        
        return jsonify({
            'success': True,
            'test_mode_active': is_active,
            'test_info': test_info,
            'details': {
                'system_architecture': system_arch,
                'current_ffmpeg_architecture': current_arch,
                'is_compatible': current_arch == system_arch if current_arch else None
            }
        })
        
    except Exception as e:
        error_msg = f"Error checking test mode: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg,
            'test_mode_active': False
        }), 500

def main():
    """Main entry point for the application"""
    max_retries = 5
    retries = 0
    
    # Wait for port to become available
    while is_port_in_use(APP_PORT) and retries < max_retries:
        logging.info(f"Waiting for port {APP_PORT} to be available...")
        time.sleep(1)
        retries += 1
    
    if is_port_in_use(APP_PORT):
        print(f"Error: Port {APP_PORT} is still in use. Please ensure no other applications are using this port.")
        sys.exit(1)
    
    # Start the application
    try:
        print(f"Access the application at: http://127.0.0.1:{APP_PORT}")
        serve(
            app,
            host='127.0.0.1',
            port=APP_PORT,  # Use the global port number
            threads=4
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
