document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const embyPathInput = document.getElementById('emby-path');
    const browseButton = document.getElementById('browse-button');
    const usePathButton = document.getElementById('use-path-button');
    const selectedPathElement = document.getElementById('selected-path');
    const checkCompatibilityButton = document.getElementById('check-compatibility-button');
    const compatibilityResults = document.getElementById('compatibility-results');
    const systemArchitectureElement = document.getElementById('system-architecture');
    const ffmpegArchitectureElement = document.getElementById('ffmpeg-architecture');
    const compatibilityStatusElement = document.getElementById('compatibility-status');
    const fixSection = document.getElementById('fix-section');
    const fixButton = document.getElementById('fix-button');
    const fixStatusElement = document.getElementById('fix-status');
    const restoreSection = document.getElementById('restore-section');
    const checkBackupButton = document.getElementById('check-backup-button');
    const backupStatusElement = document.getElementById('backup-status');
    const restoreButton = document.getElementById('restore-button');
    const restoreStatusElement = document.getElementById('restore-status');
    const downloadLogButton = document.getElementById('download-log-button');
    const viewLogButton = document.getElementById('view-log-button');
    const logContainer = document.getElementById('log-container');
    const logEntries = document.getElementById('log-entries');

    // State
    let selectedEmbyPath = '';
    let isCompatible = false;

    // Functions
    function updateSelectedPath(path) {
        selectedEmbyPath = path;
        selectedPathElement.textContent = path;
        checkCompatibilityButton.disabled = false;
        checkBackupButton.disabled = false;
        
        // Reset compatibility results
        compatibilityResults.classList.add('hidden');
        fixSection.classList.add('hidden');
        fixStatusElement.classList.add('hidden');
        backupStatusElement.classList.add('hidden');
        restoreButton.classList.add('hidden');
        restoreStatusElement.classList.add('hidden');
    }

    function selectEmbyPath(path) {
        fetch('/api/select-emby', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ path: path })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSelectedPath(data.path);
                addLogEntry(`Selected Emby Server path: ${data.path}`);
            } else {
                alert(data.message);
                addLogEntry(`Error selecting path: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while selecting the Emby Server path');
            addLogEntry(`Error: ${error.message}`, 'error');
        });
    }

    function checkCompatibility() {
        if (!selectedEmbyPath) {
            alert('Please select Emby Server path first');
            return;
        }

        addLogEntry('Checking Emby Server Path...', 'active');
        
        fetch('/api/check-compatibility', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ path: selectedEmbyPath })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addLogEntry('Checking Emby Server Path...', 'complete');
                
                // Display system architecture
                addLogEntry('Detecting System Architecture...', 'active');
                systemArchitectureElement.textContent = data.system_architecture;
                
                // Add explanation for system architecture
                const sysArchExplanation = `System architecture refers to your computer's CPU type (Intel/AMD = x86_64, Apple Silicon = arm64)`;
                addLogEntry(sysArchExplanation);
                addLogEntry('Detecting System Architecture...', 'complete');
                
                // Display FFMPEG architecture
                addLogEntry('Detecting FFMPEG Architecture...', 'active');
                ffmpegArchitectureElement.textContent = data.ffmpeg_architecture;
                
                // Add explanation for FFMPEG architecture
                const ffmpegArchExplanation = 'FFMPEG architecture must match system architecture for Emby to work properly';
                addLogEntry(ffmpegArchExplanation);
                addLogEntry('Detecting FFMPEG Architecture...', 'complete');
                
                // Check compatibility and display status
                isCompatible = data.is_compatible;
                if (isCompatible) {
                    compatibilityStatusElement.textContent = 'Compatible ✓';
                    compatibilityStatusElement.className = 'compatible';
                    fixSection.classList.add('hidden');
                } else {
                    compatibilityStatusElement.textContent = 'Incompatible ✗';
                    compatibilityStatusElement.className = 'incompatible';
                    fixSection.classList.remove('hidden');
                }
                
                compatibilityResults.classList.remove('hidden');
            } else {
                alert(data.message);
                addLogEntry(`Error checking compatibility: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while checking compatibility');
            addLogEntry(`Error: ${error.message}`, 'error');
        });
    }

    function fixFFMPEG() {
        if (!selectedEmbyPath) {
            alert('Please select Emby Server path first');
            return;
        }

        if (isCompatible) {
            alert('FFMPEG is already compatible with your system');
            return;
        }

        addLogEntry('Fixing FFMPEG Compatibility...', 'active');
        
        fetch('/api/fix-ffmpeg', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ path: selectedEmbyPath })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                fixStatusElement.textContent = '✅ ' + data.message;
                fixStatusElement.className = 'status-message success';
                addLogEntry('Fixing FFMPEG Compatibility...', 'complete');
                addLogEntry(data.message);
                
                // After fixing, re-check compatibility
                setTimeout(checkCompatibility, 1000);
            } else {
                fixStatusElement.textContent = '❌ ' + data.message;
                fixStatusElement.className = 'status-message error';
                addLogEntry('Fixing FFMPEG Compatibility...', 'error');
                addLogEntry(data.message, 'error');
            }
            
            fixStatusElement.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error:', error);
            fixStatusElement.textContent = '❌ An error occurred while fixing FFMPEG compatibility';
            fixStatusElement.className = 'status-message error';
            fixStatusElement.classList.remove('hidden');
            addLogEntry(`Error: ${error.message}`, 'error');
        });
    }

    function checkBackup() {
        if (!selectedEmbyPath) {
            alert('Please select Emby Server path first');
            return;
        }

        addLogEntry('Checking for FFMPEG backup...', 'active');
        
        fetch('/api/check-backup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ path: selectedEmbyPath })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.has_backup) {
                    backupStatusElement.textContent = '✅ Original FFMPEG backup found';
                    backupStatusElement.className = 'status-message success';
                    restoreButton.classList.remove('hidden');
                    addLogEntry('Original FFMPEG backup found');
                } else {
                    backupStatusElement.textContent = 'ℹ️ No original FFMPEG backup found';
                    backupStatusElement.className = 'status-message info';
                    restoreButton.classList.add('hidden');
                    addLogEntry('No original FFMPEG backup found');
                }
                
                addLogEntry('Checking for FFMPEG backup...', 'complete');
            } else {
                backupStatusElement.textContent = '❌ ' + data.message;
                backupStatusElement.className = 'status-message error';
                restoreButton.classList.add('hidden');
                addLogEntry('Checking for FFMPEG backup...', 'error');
                addLogEntry(data.message, 'error');
            }
            
            backupStatusElement.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error:', error);
            backupStatusElement.textContent = '❌ An error occurred while checking for backup';
            backupStatusElement.className = 'status-message error';
            backupStatusElement.classList.remove('hidden');
            restoreButton.classList.add('hidden');
            addLogEntry(`Error: ${error.message}`, 'error');
        });
    }

    function restoreFFMPEG() {
        if (!selectedEmbyPath) {
            alert('Please select Emby Server path first');
            return;
        }

        if (!confirm('Are you sure you want to restore the original FFMPEG binaries? This will undo any fixes applied by this tool.')) {
            return;
        }

        addLogEntry('Restoring original FFMPEG binaries...', 'active');
        
        fetch('/api/restore-ffmpeg', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ path: selectedEmbyPath })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                restoreStatusElement.textContent = '✅ ' + data.message;
                restoreStatusElement.className = 'status-message success';
                addLogEntry('Restoring original FFMPEG binaries...', 'complete');
                addLogEntry(data.message);
                
                // After restoring, re-check compatibility
                setTimeout(checkCompatibility, 1000);
            } else {
                restoreStatusElement.textContent = '❌ ' + data.message;
                restoreStatusElement.className = 'status-message error';
                addLogEntry('Restoring original FFMPEG binaries...', 'error');
                addLogEntry(data.message, 'error');
            }
            
            restoreStatusElement.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error:', error);
            restoreStatusElement.textContent = '❌ An error occurred while restoring FFMPEG binaries';
            restoreStatusElement.className = 'status-message error';
            restoreStatusElement.classList.remove('hidden');
            addLogEntry(`Error: ${error.message}`, 'error');
        });
    }

    function downloadLog() {
        window.location.href = '/api/download-log';
    }

    function viewFullLog() {
        fetch('/api/get-logs')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Create modal to display full log
                const modal = document.createElement('div');
                modal.className = 'modal';
                
                const modalContent = document.createElement('div');
                modalContent.className = 'modal-content';
                
                const closeButton = document.createElement('span');
                closeButton.className = 'close-button';
                closeButton.textContent = '×';
                closeButton.onclick = () => {
                    document.body.removeChild(modal);
                };
                
                const heading = document.createElement('h2');
                heading.textContent = 'Full Log';
                
                const logText = document.createElement('pre');
                logText.className = 'full-log';
                logText.textContent = data.logs;
                
                modalContent.appendChild(closeButton);
                modalContent.appendChild(heading);
                modalContent.appendChild(logText);
                modal.appendChild(modalContent);
                
                document.body.appendChild(modal);
                
                // Close modal when clicking outside
                window.onclick = (event) => {
                    if (event.target === modal) {
                        document.body.removeChild(modal);
                    }
                };
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while retrieving logs');
        });
    }

    function addLogEntry(message, status = '') {
        const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        let statusIcon = '';
        let statusClass = '';
        
        switch (status) {
            case 'active':
                statusIcon = '▶ ';
                statusClass = 'active';
                break;
            case 'complete':
                statusIcon = '✓ ';
                statusClass = 'complete';
                break;
            case 'error':
                statusIcon = '✗ ';
                statusClass = 'error';
                break;
            default:
                statusIcon = '  ';
                break;
        }
        
        logEntry.innerHTML = `<span class="log-timestamp">${timestamp}</span> <span class="log-status ${statusClass}">${statusIcon}${message}</span>`;
        logEntries.appendChild(logEntry);
        
        // Scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Event listeners
    browseButton.addEventListener('click', function() {
        // Using a text input as a workaround since we can't directly browse in web app
        const path = prompt('Enter the path to your Emby Server application:', '/Applications/EmbyServer.app');
        if (path) {
            embyPathInput.value = path;
            selectEmbyPath(path);
        }
    });

    usePathButton.addEventListener('click', function() {
        const path = embyPathInput.value.trim();
        if (path) {
            selectEmbyPath(path);
        } else {
            alert('Please enter a valid path');
        }
    });

    checkCompatibilityButton.addEventListener('click', checkCompatibility);
    fixButton.addEventListener('click', fixFFMPEG);
    checkBackupButton.addEventListener('click', checkBackup);
    restoreButton.addEventListener('click', restoreFFMPEG);
    downloadLogButton.addEventListener('click', downloadLog);
    viewLogButton.addEventListener('click', viewFullLog);

    // Initialize with a log entry
    const currentDate = new Date().toISOString().substring(0, 10);
    const currentTime = new Date().toTimeString().substring(0, 8);
    addLogEntry(`${currentDate} ${currentTime} Initialization`, 'complete');
});
