document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const embyPathInput = document.getElementById('embyPath');
    const browseButton = document.getElementById('browseEmby');
    const usePathButton = document.getElementById('useThisPath');
    const selectedPathDisplay = document.getElementById('selected-path');
    const checkCompatibilityButton = document.getElementById('check-compatibility');
    const stopProcessButton = document.getElementById('stop-process');
    const compatibilityResults = document.getElementById('compatibility-results');
    const systemArchitectureElement = document.getElementById('system-architecture');
    const ffmpegArchitectureElement = document.getElementById('ffmpeg-architecture');
    const compatibilityStatusElement = document.getElementById('compatibility-status');
    const fixSection = document.getElementById('fix-section');
    const fixButton = document.getElementById('fix-compatibility');
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
    let currentStep = null;
    let isProcessing = false;

    // Event Listeners
    if (stopProcessButton) {
        stopProcessButton.addEventListener('click', function() {
            if (isProcessing) {
                stopProcess();
            }
        });
        
        // Initialize stop button state
        stopProcessButton.disabled = true;
        stopProcessButton.classList.add('disabled');
        stopProcessButton.setAttribute('title', 'No process running');
        stopProcessButton.style.cursor = 'not-allowed';
        stopProcessButton.style.opacity = '0.65';
    }
    
    // Initialize the application
    initializeApp();

    // Progress tracking
    const progressSteps = {
        'check-compatibility': { progress: 0, status: 'pending' },
        'fix-compatibility': { progress: 0, status: 'pending' },
        'restore': { progress: 0, status: 'pending' }
    };

    function updateProgress(step, progress, status = null) {
        if (progressSteps[step]) {
            progressSteps[step].progress = progress;
            if (status) {
                progressSteps[step].status = status;
            }

            const progressBar = document.querySelector(`.progress-item[data-step="${step}"] .progress-bar`);
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
                progressBar.classList.remove('complete', 'error', 'stalled');
                if (status) {
                    progressBar.classList.add(status);
                }
            }
        }
    }

    function resetProgress() {
        Object.keys(progressSteps).forEach(step => {
            progressSteps[step].progress = 0;
            progressSteps[step].status = 'pending';
            updateProgress(step, 0);
        });
    }

    function setProcessing(processing) {
        console.log('Setting processing state:', processing); // Debug log
        isProcessing = processing;
        
        // Update button states
        if (stopProcessButton) {
            stopProcessButton.disabled = !processing;
            
            if (processing) {
                console.log('Enabling stop button'); // Debug log
                stopProcessButton.classList.remove('disabled');
                stopProcessButton.setAttribute('title', 'Stop current process');
                stopProcessButton.style.removeProperty('cursor');
                stopProcessButton.style.removeProperty('opacity');
                stopProcessButton.classList.add('pulse-animation');
            } else {
                console.log('Disabling stop button'); // Debug log
                stopProcessButton.classList.add('disabled');
                stopProcessButton.setAttribute('title', 'No process running');
                stopProcessButton.classList.remove('pulse-animation');
            }
        }
        
        // Update other button states
        if (checkCompatibilityButton) checkCompatibilityButton.disabled = processing;
        if (fixButton) fixButton.disabled = processing;
        if (restoreButton) restoreButton.disabled = processing;
        if (checkBackupButton) checkBackupButton.disabled = processing;
        
        // Update progress bars if stopping
        if (!processing) {
            resetProgress();
        }
    }

    function stopProcess() {
        if (!isProcessing) return;

        const mainEntryId = addLogEntry('Stopping process...', 'active');
        
        fetch('/api/stop-process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                path: selectedEmbyPath
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addLogEntry('Process stopped by user', 'complete', true, mainEntryId);
                addLogEntry('Restoring to initial state...', 'active', true, mainEntryId);
                setProcessing(false);
                // Reset all progress bars
                resetProgress();
                // Update current step's progress to stopped state
                if (currentStep) {
                    updateProgress(currentStep, 100, 'error');
                }
                // Clear results and reset UI
                compatibilityResults.classList.add('hidden');
                fixSection.classList.add('hidden');
                restoreSection.classList.add('hidden');
                
                // Handle redirect
                if (data.redirect) {
                    addLogEntry('Initial state restored, redirecting to start page...', 'complete', true, mainEntryId);
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1000);
                }
            } else {
                addLogEntry(`Failed to stop process: ${data.message}`, 'error', true, mainEntryId);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addLogEntry(`Error stopping process: ${error.message}`, 'error', true, mainEntryId);
        });
    }

    function initializeApp() {
        const currentDate = new Date().toISOString().substring(0, 10);
        const currentTime = new Date().toTimeString().substring(0, 8);
        addLogEntry(`${currentDate} ${currentTime} Initialization`, 'complete');
        
        // Check current processing state from server
        fetch('/api/process-state')
            .then(response => response.json())
            .then(data => {
                setProcessing(data.is_processing);
                if (data.is_processing) {
                    addLogEntry('Process is currently running', 'active');
                }
            })
            .catch(error => {
                console.error('Error getting process state:', error);
                setProcessing(false);
            });
        
        // If there's a pre-populated path, trigger the path selection
        if (embyPathInput && embyPathInput.value) {
            selectedEmbyPath = embyPathInput.value;
            updateSelectedPath(embyPathInput.value);
            addLogEntry(`Selected Emby Server path: ${embyPathInput.value}`, 'complete');
        } else {
            // Try to get default path from server
            fetch('/api/get-default-path')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.path) {
                        selectedEmbyPath = data.path;
                        embyPathInput.value = data.path;
                        updateSelectedPath(data.path);
                        addLogEntry(`Found default Emby Server path: ${data.path}`, 'complete');
                    }
                })
                .catch(error => {
                    console.error('Error getting default path:', error);
                });
        }
    }

    // Functions
    function updateSelectedPath(path) {
        selectedEmbyPath = path;
        selectedPathDisplay.textContent = path;
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

    async function selectEmbyPath(path) {
        try {
            const response = await fetch('/api/select-emby', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ path: path })
            });
            
            const data = await response.json();
            
            if (data.success) {
                updateSelectedPath(data.path);
                addLogEntry(`Selected Emby Server path: ${data.path}`);
                return data;
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            addLogEntry(`Error selecting path: ${error.message}`, 'error');
            throw error;
        }
    }

    function checkCompatibility() {
        if (!selectedEmbyPath) {
            alert('Please select Emby Server path first');
            return;
        }

        currentStep = 'check-compatibility';
        setProcessing(true);  // Set processing state at the start
        resetProgress();
        updateProgress('check-compatibility', 10, 'active');
        
        const mainEntryId = addLogEntry('Checking Emby Server Path...', 'active');
        
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
                updateProgress('check-compatibility', 40);
                addLogEntry('Path validation successful', 'complete', true, mainEntryId);
                
                // Display system architecture
                addLogEntry('Detecting System Architecture...', 'active', true, mainEntryId);
                updateProgress('check-compatibility', 60);
                systemArchitectureElement.textContent = data.system_architecture;
                addLogEntry(`System Architecture: ${data.system_architecture}`, 'complete', true, mainEntryId);
                
                // Display FFMPEG architecture
                addLogEntry('Detecting FFMPEG Architecture...', 'active', true, mainEntryId);
                updateProgress('check-compatibility', 80);
                ffmpegArchitectureElement.textContent = data.ffmpeg_architecture;
                addLogEntry(`FFMPEG Architecture: ${data.ffmpeg_architecture}`, 'complete', true, mainEntryId);
                
                // Check compatibility and display status
                isCompatible = data.is_compatible;
                updateProgress('check-compatibility', 100, 'complete');
                
                if (isCompatible) {
                    compatibilityStatusElement.textContent = 'Compatible ✓';
                    compatibilityStatusElement.style.color = '#28a745';
                    fixSection.classList.add('hidden');
                    addLogEntry('Compatibility check complete - System is compatible', 'complete', true, mainEntryId);
                } else {
                    compatibilityStatusElement.textContent = 'Incompatible ✗';
                    compatibilityStatusElement.style.color = '#dc3545';
                    fixSection.classList.remove('hidden');
                    addLogEntry('⚠️ FFMPEG binaries are incompatible with your system architecture', 'error', true, mainEntryId);
                }
                
                compatibilityResults.classList.remove('hidden');
            } else {
                updateProgress('check-compatibility', 100, 'error');
                alert(data.message);
                addLogEntry(`Error checking compatibility: ${data.message}`, 'error', true, mainEntryId);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            updateProgress('check-compatibility', 100, 'error');
            alert('An error occurred while checking compatibility');
            addLogEntry(`Error: ${error.message}`, 'error', true, mainEntryId);
        })
        .finally(() => {
            setProcessing(false);  // Only set processing to false when the operation is complete
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

        setProcessing(true);  // Set processing state at the start
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
                setProcessing(false);  // Set processing to false on error
            }
            
            fixStatusElement.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error:', error);
            fixStatusElement.textContent = '❌ An error occurred while fixing FFMPEG compatibility';
            fixStatusElement.className = 'status-message error';
            fixStatusElement.classList.remove('hidden');
            addLogEntry(`Error: ${error.message}`, 'error');
            setProcessing(false);  // Set processing to false on error
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
        addLogEntry('Fetching full log...', 'active');
        
        fetch('/api/get-logs', {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                console.error('Response not OK:', response.status, response.statusText);
                if (response.status === 404) {
                    throw new Error('Log file not found');
                } else if (response.status === 500) {
                    throw new Error('Server error while reading logs');
                } else {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            }
            return response.json().catch(error => {
                console.error('JSON parse error:', error);
                throw new Error('Failed to parse server response');
            });
        })
        .then(data => {
            if (!data) {
                throw new Error('No data received from server');
            }
            
            if (data.success) {
                if (!data.logs) {
                    throw new Error('Log data is empty');
                }
                
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
                
                try {
                    // Split logs into lines and reverse them
                    const logLines = data.logs.split('\n').reverse();
                    logText.textContent = logLines.join('\n');
                } catch (error) {
                    console.error('Error processing log data:', error);
                    throw new Error('Error processing log data');
                }
                
                modalContent.appendChild(closeButton);
                modalContent.appendChild(heading);
                modalContent.appendChild(logText);
                modal.appendChild(modalContent);
                
                // Remove any existing modals
                const existingModal = document.querySelector('.modal');
                if (existingModal) {
                    document.body.removeChild(existingModal);
                }
                
                document.body.appendChild(modal);
                
                // Close modal when clicking outside
                window.onclick = (event) => {
                    if (event.target === modal) {
                        document.body.removeChild(modal);
                    }
                };
                
                addLogEntry('Successfully loaded full log', 'complete');
            } else {
                throw new Error(data.message || 'Failed to load logs');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addLogEntry(`Error loading logs: ${error.message}`, 'error');
            
            // Show error in a modal instead of an alert
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
            heading.textContent = 'Error Loading Logs';
            heading.style.color = '#dc3545';
            
            const errorMessage = document.createElement('p');
            errorMessage.textContent = error.message;
            errorMessage.style.color = '#721c24';
            errorMessage.style.backgroundColor = '#f8d7da';
            errorMessage.style.padding = '10px';
            errorMessage.style.borderRadius = '4px';
            
            const debugInfo = document.createElement('pre');
            debugInfo.textContent = `Time: ${new Date().toISOString()}\nError: ${error.stack || error.message}`;
            debugInfo.style.fontSize = '12px';
            debugInfo.style.marginTop = '10px';
            debugInfo.style.padding = '10px';
            debugInfo.style.backgroundColor = '#f8f9fa';
            
            modalContent.appendChild(closeButton);
            modalContent.appendChild(heading);
            modalContent.appendChild(errorMessage);
            modalContent.appendChild(debugInfo);
            modal.appendChild(modalContent);
            
            // Remove any existing modals
            const existingModal = document.querySelector('.modal');
            if (existingModal) {
                document.body.removeChild(existingModal);
            }
            
            document.body.appendChild(modal);
            
            // Close modal when clicking outside
            window.onclick = (event) => {
                if (event.target === modal) {
                    document.body.removeChild(modal);
                }
            };
        });
    }

    function addLogEntry(message, status = '', isSubstep = false, parentId = null) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        const timestamp = new Date().toLocaleTimeString();
        
        if (!isSubstep) {
            entry.id = 'log_' + Date.now();
            entry.innerHTML = `
                <span class="disclosure-triangle">▶</span>
                <span class="log-timestamp">${timestamp}</span>
                <span class="log-step">${message}</span>
                ${status ? `<span class="log-status ${status}">${status}</span>` : ''}
                <div class="substeps"></div>
            `;
            
            entry.addEventListener('click', () => {
                entry.classList.toggle('expanded');
            });
            
            logEntries.appendChild(entry);
        } else if (parentId) {
            const parent = document.getElementById(parentId);
            if (parent) {
                const substeps = parent.querySelector('.substeps');
                const substep = document.createElement('div');
                substep.className = 'log-entry substep';
                substep.innerHTML = `
                    <span class="log-timestamp">${timestamp}</span>
                    <span class="log-step">${message}</span>
                    ${status ? `<span class="log-status ${status}">${status}</span>` : ''}
                `;
                substeps.appendChild(substep);
                parent.classList.add('has-substeps');
            }
        }
        
        logContainer.scrollTop = logContainer.scrollHeight;
        return entry.id;
    }

    function forceArchitecture(arch) {
        if (!selectedEmbyPath) {
            alert('Please select Emby Server path first');
            return;
        }

        if (!confirm(`Are you sure you want to force ${arch} architecture? This is for testing purposes only.`)) {
            return;
        }

        addLogEntry(`Forcing ${arch} architecture for testing...`, 'active');
        
        fetch('/api/force-test-mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                path: selectedEmbyPath,
                architecture: arch
            })
        })
        .then(response => response.json())
        .then(data => {
            const statusElement = document.getElementById('test-mode-status');
            if (data.success) {
                statusElement.textContent = '✅ ' + data.message;
                statusElement.className = 'status-message success';
                addLogEntry(`Forcing ${arch} architecture...`, 'complete');
                addLogEntry(data.message);
                
                // After forcing architecture, re-check compatibility
                setTimeout(checkCompatibility, 1000);
            } else {
                statusElement.textContent = '❌ ' + data.message;
                statusElement.className = 'status-message error';
                addLogEntry(`Forcing ${arch} architecture...`, 'error');
                addLogEntry(data.message, 'error');
            }
            
            statusElement.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error:', error);
            const statusElement = document.getElementById('test-mode-status');
            statusElement.textContent = '❌ An error occurred while forcing architecture';
            statusElement.className = 'status-message error';
            statusElement.classList.remove('hidden');
            addLogEntry(`Error: ${error.message}`, 'error');
        });
    }

    // Event listeners
    if (browseButton) {
        browseButton.addEventListener('click', function() {
            fetch('/api/browse-emby', {
                method: 'GET'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.path) {
                    embyPathInput.value = data.path;
                    updateSelectedPath(data.path);
                    addLogEntry(`Selected Emby Server path: ${data.path}`, 'complete');
                } else if (data.message) {
                    addLogEntry(`Failed to select path: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                addLogEntry(`Error selecting path: ${error.message}`, 'error');
            });
        });
    }

    usePathButton.addEventListener('click', function() {
        const path = embyPathInput.value.trim();
        if (path) {
            selectEmbyPath(path)
                .then(() => {
                    addLogEntry('Successfully validated entered path', 'complete');
                    // Automatically check compatibility after path is validated
                    checkCompatibility();
                })
                .catch(error => {
                    alert(error.message);
                });
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

    document.getElementById('force-x86-button').addEventListener('click', () => forceArchitecture('x86_64'));
    document.getElementById('force-arm-button').addEventListener('click', () => forceArchitecture('arm64'));
});
