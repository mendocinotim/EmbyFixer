from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import platform
import subprocess
import logging
from datetime import datetime
from utils import (
    get_system_architecture, 
    find_ffmpeg_binaries,
    get_ffmpeg_architecture,
    backup_original_ffmpeg,
    restore_original_ffmpeg,
    replace_ffmpeg_binaries
)

app = Flask(__name__)

# Configure logging
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

log_file = os.path.join(logs_dir, 'emby_ffmpeg_fixer.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/select-emby', methods=['POST'])
def select_emby():
    emby_path = request.json.get('path')
    
    if not emby_path or not os.path.exists(emby_path):
        return jsonify({
            'success': False,
            'message': 'Invalid Emby Server path'
        })
    
    # Save the selected path for later use
    app.config['EMBY_PATH'] = emby_path
    
    return jsonify({
        'success': True,
        'path': emby_path
    })

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
    emby_path = request.json.get('path')
    
    if not emby_path or not os.path.exists(emby_path):
        return jsonify({
            'success': False,
            'message': 'Invalid Emby Server path'
        })
    
    # Restore original FFMPEG binaries
    success, message = restore_original_ffmpeg(emby_path)
    
    return jsonify({
        'success': success,
        'message': message
    })

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

@app.route('/api/get-logs')
def get_logs():
    try:
        with open(log_file, 'r') as f:
            logs = f.read()
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/download-log')
def download_log():
    return send_file(log_file, as_attachment=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)
