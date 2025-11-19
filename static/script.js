class SSHEmulator {
    constructor() {
        this.sessionId = null;
        this.websocket = null;
        this.isConnected = false;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.paginationEnabled = true; // Auto-handle pagination like Putty_own.py
        this.lastSentCommand = null; // Track last sent command to filter echoes
        this.deviceType = null; // Track device type for specific commands
        this.learnedCommands = this.loadLearnedCommands(); // Load saved commands from localStorage
        this.availableCommands = [ // Common SSH commands for autocompletion
            'ls', 'cd', 'pwd', 'mkdir', 'rm', 'cp', 'mv', 'cat', 'less', 'more',
            'grep', 'find', 'chmod', 'chown', 'tar', 'gzip', 'ping', 'ssh',
            'scp', 'rsync', 'ps', 'top', 'kill', 'systemctl', 'service',
            'ifconfig', 'ip', 'netstat', 'df', 'du', 'free', 'uname',
            'whoami', 'id', 'date', 'uptime', 'history', 'exit', 'clear',
            'sudo', 'su', 'passwd', 'crontab', 'wget', 'curl', 'git'
        ];
        this.fileCache = []; // Cache for file/directory names
        this.currentPath = '~'; // Track current directory
        
        this.initializeElements();
        this.bindEvents();
        this.loadSavedSession();
    }

    loadLearnedCommands() {
        try {
            const saved = localStorage.getItem('learnedCommands');
            return saved ? JSON.parse(saved) : {};
        } catch (e) {
            console.error('Error loading learned commands:', e);
            return {};
        }
    }
    
    saveLearnedCommands() {
        try {
            localStorage.setItem('learnedCommands', JSON.stringify(this.learnedCommands));
        } catch (e) {
            console.error('Error saving learned commands:', e);
        }
    }
    
    addLearnedCommand(command) {
        // Extract the command name (first word)
        const commandName = command.trim().split(/\s+/)[0];
        if (!commandName || commandName.length < 2) return; // Skip very short commands
        
        // Get the key for storing (device-specific or global)
        const key = this.deviceType || 'global';
        
        // Initialize the command set if needed
        if (!this.learnedCommands[key]) {
            this.learnedCommands[key] = new Set();
        }
        
        // Add the command if not already present
        if (!this.learnedCommands[key].has(commandName)) {
            this.learnedCommands[key].add(commandName);
            
            // Keep the list manageable (max 200 commands per device type)
            if (this.learnedCommands[key].size > 200) {
                const commandsArray = Array.from(this.learnedCommands[key]);
                // Keep the most recent 100 commands
                commandsArray.splice(0, commandsArray.length - 100);
                this.learnedCommands[key] = new Set(commandsArray);
            }
            
            // Save to localStorage
            this.saveLearnedCommands();
        }
    }
    
    getLearnedCommands() {
        const commands = new Set();
        
        // Add global commands
        if (this.learnedCommands.global) {
            this.learnedCommands.global.forEach(cmd => commands.add(cmd));
        }
        
        // Add device-specific commands
        if (this.deviceType && this.learnedCommands[this.deviceType]) {
            this.learnedCommands[this.deviceType].forEach(cmd => commands.add(cmd));
        }
        
        return Array.from(commands);
    }

    initializeElements() {
        // Connection elements
        this.hostInput = document.getElementById('host');
        this.portInput = document.getElementById('port');
        this.usernameInput = document.getElementById('username');
        this.passwordInput = document.getElementById('password');
        this.connectBtn = document.getElementById('connect-btn');
        this.disconnectBtn = document.getElementById('disconnect-btn');
        this.saveSessionBtn = document.getElementById('save-session-btn');
        this.loadSessionBtn = document.getElementById('load-session-btn');
        
        // Status elements
        this.statusDot = document.getElementById('connection-status');
        this.statusText = document.getElementById('status-text');
        
        // Terminal elements
        this.terminalOutput = document.getElementById('terminal-output');
        this.terminalInput = document.getElementById('terminal-input');
        this.sendBtn = document.getElementById('send-btn');
        this.clearTerminalBtn = document.getElementById('clear-terminal');
        this.copyBtn = document.getElementById('copy-output');
        this.saveOutputBtn = document.getElementById('save-output');
        
        // Pagination elements (exactly like Putty_own.py)
        this.autoPaginationCheckbox = document.getElementById('auto-pagination');
        this.sendSpaceBtn = document.getElementById('send-space');
        
        // Loading overlay
        this.loadingOverlay = document.getElementById('loading-overlay');
        
        // Quick command buttons
        this.commandButtons = document.querySelectorAll('.cmd-btn');
        
        // Fullscreen element
        this.fullscreenBtn = document.getElementById('fullscreen');
        
        // Configuration upload elements
        this.configFileInput = document.getElementById('config-file');
        this.uploadArea = document.getElementById('upload-area');
        this.fileInfo = document.getElementById('file-info');
        this.fileName = document.getElementById('file-name');
        this.fileSize = document.getElementById('file-size');
        this.clearFileBtn = document.getElementById('clear-file');
        this.uploadBtn = document.getElementById('upload-btn');
        this.batchCommandsText = document.getElementById('batch-commands-text');
        this.executeBatchBtn = document.getElementById('execute-batch');
        this.clearBatchBtn = document.getElementById('clear-batch');
        this.saveBatchBtn = document.getElementById('save-batch');
        this.tabBtns = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');
    }

    bindEvents() {
        // Connection events
        this.connectBtn.addEventListener('click', () => this.connect());
        this.disconnectBtn.addEventListener('click', () => this.disconnect());
        this.saveSessionBtn.addEventListener('click', () => this.saveSession());
        this.loadSessionBtn.addEventListener('click', () => this.loadSession());
        
        // Terminal events
        this.sendBtn.addEventListener('click', () => this.sendCommand());
        this.terminalInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendCommand();
            }
        });
        
        // Tab key for autocompletion
        this.terminalInput.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                e.preventDefault();
                this.autocompleteCommand();
            }
        });
        
        // Command history navigation
        this.terminalInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateHistory(-1);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateHistory(1);
            }
        });
        
        // Terminal controls
        this.clearTerminalBtn.addEventListener('click', () => this.clearTerminal());
        this.copyBtn.addEventListener('click', () => this.copyTerminal());
        this.saveOutputBtn.addEventListener('click', () => this.saveOutput());
        
        // Pagination controls (exactly like Putty_own.py)
        this.autoPaginationCheckbox.addEventListener('change', () => this.togglePagination());
        this.sendSpaceBtn.addEventListener('click', () => this.sendSpace());
        
        // Quick command buttons
        this.commandButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const command = btn.getAttribute('data-command');
                this.terminalInput.value = command;
                this.terminalInput.focus();
            });
        });
        
        // Fullscreen control
        this.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        
        // Tab switching
        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.getAttribute('data-tab')));
        });
        
        // File upload events
        this.configFileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.clearFileBtn.addEventListener('click', () => this.clearFile());
        this.uploadBtn.addEventListener('click', () => this.uploadConfig());
        
        // Drag and drop
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleFileDrop(e));
        
        // Batch commands events
        this.executeBatchBtn.addEventListener('click', () => this.executeBatchCommands());
        this.clearBatchBtn.addEventListener('click', () => this.clearBatchCommands());
        this.saveBatchBtn.addEventListener('click', () => this.saveBatchTemplate());
        
        // Enter key on input fields
        [this.hostInput, this.portInput, this.usernameInput, this.passwordInput].forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.connect();
                }
            });
        });
    }

    async connect() {
        const host = this.hostInput.value.trim();
        const port = this.portInput.value.trim() || '22';
        const username = this.usernameInput.value.trim();
        const password = this.passwordInput.value;

        if (!host || !username || !password) {
            this.showNotification('Please fill in all connection details', 'error');
            return;
        }

        this.showLoading(true);
        this.updateStatus('connecting', 'Connecting...');

        try {
            const response = await fetch('/api/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    host,
                    port: parseInt(port),
                    username,
                    password
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Connection failed');
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            
            // Establish WebSocket connection
            await this.connectWebSocket();
            
            this.isConnected = true;
            this.updateConnectionUI(true);
            this.updateStatus('connected', 'Connected');
            this.showNotification('SSH connection established', 'success');
            
        } catch (error) {
            console.error('Connection error:', error);
            this.updateStatus('disconnected', 'Connection Failed');
            this.showNotification(`Connection failed: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async connectWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws/${this.sessionId}`;
        this.websocket = new WebSocket(wsUrl);

        return new Promise((resolve, reject) => {
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                resolve();
            };

            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.handleDisconnect();
            };

            // Timeout after 10 seconds
            setTimeout(() => {
                if (this.websocket.readyState !== WebSocket.OPEN) {
                    reject(new Error('WebSocket connection timeout'));
                }
            }, 10000);
        });
    }

    handleWebSocketMessage(data) {
        if (data.type === 'output') {
            // Handle pagination exactly like Putty_own.py
            let processedData = data.data;
            
            // Detect device type from output
            this.detectDeviceType(processedData);
            
            // Check for --More-- prompt
            if (processedData.includes('--More--')) {
                if (this.paginationEnabled) {
                    // Auto-send space for pagination
                    this.sendSpace(false); // Don't show message when auto-sending
                    processedData = processedData.replace('--More--', '[More...]');
                } else {
                    // Enable the Send Space button when pagination is manual
                    this.sendSpaceBtn.disabled = false;
                }
            } else {
                // Disable Send Space button when not in pagination mode
                this.sendSpaceBtn.disabled = true;
            }
            
            // Filter out command echoes
            if (this.lastSentCommand) {
                const lines = processedData.split('\n');
                const filteredLines = [];
                
                for (let line of lines) {
                    // Remove empty lines
                    if (!line.trim()) continue;
                    
                    // Check if line contains the last sent command
                    const cleanLine = line.trim();
                    const cleanCommand = this.lastSentCommand.trim();
                    
                    // Skip if line is exactly the command
                    if (cleanLine === cleanCommand) {
                        console.log('Filtering exact match:', line);
                        continue;
                    }
                    
                    // Skip if line ends with the command and has a prompt prefix
                    if (cleanLine.endsWith(cleanCommand) && 
                        (cleanLine.startsWith('$') || cleanLine.startsWith('#') || cleanLine.startsWith('>'))) {
                        console.log('Filtering prompt match:', line);
                        continue;
                    }
                    
                    // Skip if line contains the command (more lenient)
                    if (cleanLine.includes(cleanCommand)) {
                        console.log('Filtering contains match:', line);
                        continue;
                    }
                    
                    filteredLines.push(line);
                }
                
                if (filteredLines.length > 0) {
                    this.appendTerminalOutput(filteredLines.join('\n'));
                }
                
                // Clear the last sent command after processing
                this.lastSentCommand = null;
            } else {
                // No command to filter, show all output
                this.appendTerminalOutput(processedData);
            }
        } else if (data.type === 'error') {
            this.appendTerminalOutput(`\n[ERROR] ${data.message}\n`, 'error');
        } else if (data.type === 'filelist') {
            // Filelist responses are handled by the requestFileList method
            // Don't display them in the terminal
            return;
        }
    }
    
    detectDeviceType(output) {
        // Only detect if device type is not already set
        if (this.deviceType) return;
        
        const outputLower = output.toLowerCase();
        
        // Cisco IOS detection
        if (outputLower.includes('cisco') || 
            outputLower.includes('ios software') ||
            outputLower.includes('cisco ios software') ||
            outputLower.match(/router\#/i) ||
            outputLower.match(/switch\#/i) ||
            outputLower.includes('cisco systems')) {
            this.deviceType = 'cisco';
            this.showNotification('Cisco device detected - using Cisco commands', 'success');
            return;
        }
        
        // Juniper Junos detection
        if (outputLower.includes('juniper') ||
            outputLower.includes('junos') ||
            outputLower.includes('junos os') ||
            outputLower.match(/user@.*>/i) ||
            outputLower.match(/user@.*\#/i)) {
            this.deviceType = 'juniper';
            this.showNotification('Juniper device detected - using Junos commands', 'success');
            return;
        }
        
        // Arista EOS detection
        if (outputLower.includes('arista') ||
            outputLower.includes('eos') ||
            outputLower.includes('arista networks') ||
            outputLower.match(/.*\#.*eos/i)) {
            this.deviceType = 'arista';
            this.showNotification('Arista device detected - using EOS commands', 'success');
            return;
        }
        
        // Huawei VRP detection
        if (outputLower.includes('huawei') ||
            outputLower.includes('vrp') ||
            outputLower.includes('huawei versatile routing platform') ||
            outputLower.match(/\[.*\]/i) ||
            outputLower.includes('huawei technologies')) {
            this.deviceType = 'huawei';
            this.showNotification('Huawei device detected - using VRP commands', 'success');
            return;
        }
        
        // Linux/Unix detection (default)
        if (outputLower.includes('linux') ||
            outputLower.includes('unix') ||
            outputLower.match(/.*\$/i) ||
            outputLower.includes('welcome to')) {
            this.deviceType = 'linux';
            // Don't show notification for Linux as it's the default
            return;
        }
    }

    async disconnect() {
        try {
            if (this.sessionId) {
                await fetch(`/api/disconnect/${this.sessionId}`, {
                    method: 'POST'
                });
            }
            
            if (this.websocket) {
                this.websocket.close();
            }
            
            this.handleDisconnect();
            this.showNotification('Disconnected from SSH server', 'info');
            
        } catch (error) {
            console.error('Disconnect error:', error);
        }
    }

    handleDisconnect() {
        this.isConnected = false;
        this.sessionId = null;
        this.websocket = null;
        this.updateConnectionUI(false);
        this.updateStatus('disconnected', 'Disconnected');
    }

    sendCommand() {
        const command = this.terminalInput.value;
        if (!command.trim() || !this.isConnected) return;

        // Add to command history
        this.commandHistory.push(command);
        this.historyIndex = this.commandHistory.length;
        
        // Learn this command for future autocompletion
        this.addLearnedCommand(command);

        // Track the command to filter its echo
        this.lastSentCommand = command.trim();

        // Display the command in terminal
        this.appendTerminalOutput(`\n${command}\n`, 'command');

        // Send via WebSocket
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'command',
                command: command + '\n'
            }));
        }

        // Clear input
        this.terminalInput.value = '';
    }
    
    autocompleteCommand() {
        const input = this.terminalInput.value;
        const cursorPos = this.terminalInput.selectionStart;
        
        // Get the current word being typed
        const beforeCursor = input.substring(0, cursorPos);
        const afterCursor = input.substring(cursorPos);
        const words = beforeCursor.split(/\s+/);
        const currentWord = words[words.length - 1] || '';
        
        // If current word is empty, don't autocomplete
        if (!currentWord) return;
        
        // Check if we're completing a command (first word) or file path (subsequent words)
        const isCompletingCommand = words.length === 1;
        
        if (isCompletingCommand) {
            // Complete commands - use learned commands first, then default commands
            const learnedCommands = this.getLearnedCommands();
            const allCommands = [...learnedCommands, ...this.availableCommands];
            
            // Remove duplicates while preserving order (learned commands first)
            const uniqueCommands = [...new Set(allCommands)];
            
            const matches = uniqueCommands.filter(cmd => 
                cmd.toLowerCase().startsWith(currentWord.toLowerCase())
            );
            
            if (matches.length === 0) {
                this.showNotification('No command matches found', 'info');
                return;
            }
            
            this.handleCompletion(matches, currentWord, beforeCursor, afterCursor, true);
        } else {
            // Complete file paths
            this.completeFilePath(currentWord, beforeCursor, afterCursor);
        }
    }
    
    completeFilePath(currentWord, beforeCursor, afterCursor) {
        // Extract the path to complete
        let pathToComplete = currentWord;
        let basePath = '';
        
        // Handle absolute and relative paths
        if (currentWord.includes('/')) {
            const lastSlash = currentWord.lastIndexOf('/');
            basePath = currentWord.substring(0, lastSlash + 1);
            pathToComplete = currentWord.substring(lastSlash + 1);
        }
        
        // Request file listing from server
        this.requestFileList(basePath).then(files => {
            if (!files || files.length === 0) {
                this.showNotification('No files found', 'info');
                return;
            }
            
            // Filter files that match what we're typing
            const matches = files.filter(file => 
                file.startsWith(pathToComplete)
            );
            
            if (matches.length === 0) {
                this.showNotification('No matches found', 'info');
                return;
            }
            
            // Handle file completion
            this.handleCompletion(matches, currentWord, beforeCursor, afterCursor, false, basePath);
        }).catch(err => {
            console.error('Error requesting file list:', err);
            this.showNotification('Failed to get file list', 'error');
        });
    }
    
    async requestFileList(path = '') {
        return new Promise((resolve, reject) => {
            // Create a temporary message handler for the file list response
            const tempHandler = (data) => {
                if (data.type === 'filelist') {
                    this.websocket.removeEventListener('message', tempHandler);
                    resolve(data.files || []);
                }
            };
            
            // Add temporary handler
            this.websocket.addEventListener('message', tempHandler);
            
            // Send file list request
            this.websocket.send(JSON.stringify({
                type: 'filelist',
                path: path
            }));
            
            // Timeout after 2 seconds
            setTimeout(() => {
                this.websocket.removeEventListener('message', tempHandler);
                reject(new Error('Timeout'));
            }, 2000);
        });
    }
    
    handleCompletion(matches, currentWord, beforeCursor, afterCursor, isCommand = false, basePath = '') {
        if (matches.length === 1) {
            // Single match - complete it
            const completion = matches[0];
            const isDirectory = !isCommand && completion.endsWith('/');
            
            const beforeWord = beforeCursor.substring(0, beforeCursor.length - currentWord.length);
            const completedText = basePath + completion;
            
            // Add space after command, slash after directory, or space after file
            const suffix = isCommand ? ' ' : (isDirectory ? '' : ' ');
            
            this.terminalInput.value = beforeWord + completedText + suffix + afterCursor;
            
            // Set cursor position after the completed text
            this.terminalInput.selectionStart = this.terminalInput.selectionEnd = 
                beforeWord.length + completedText.length + suffix.length;
        } else {
            // Multiple matches - show them
            const matchList = matches.slice(0, 10).join('  ');
            const moreText = matches.length > 10 ? `\n(+${matches.length - 10} more)` : '';
            this.appendTerminalOutput(`\n${matchList}${moreText}\n`, 'info');
            
            // Find the longest common prefix
            const prefix = this.findCommonPrefix(matches);
            if (prefix && prefix !== currentWord) {
                const beforeWord = beforeCursor.substring(0, beforeCursor.length - currentWord.length);
                const completedText = basePath + prefix;
                this.terminalInput.value = beforeWord + completedText + afterCursor;
                this.terminalInput.selectionStart = this.terminalInput.selectionEnd = 
                    beforeWord.length + completedText.length;
            }
        }
    }
    
    findCommonPrefix(strings) {
        if (!strings || strings.length === 0) return '';
        if (strings.length === 1) return strings[0];
        
        const first = strings[0];
        let prefix = '';
        
        for (let i = 0; i < first.length; i++) {
            const char = first[i];
            const allMatch = strings.every(s => s[i] === char);
            
            if (allMatch) {
                prefix += char;
            } else {
                break;
            }
        }
        
        return prefix;
    }
    
    navigateHistory(direction) {
        if (this.commandHistory.length === 0) return;

        this.historyIndex += direction;
        
        if (this.historyIndex < 0) {
            this.historyIndex = 0;
        } else if (this.historyIndex >= this.commandHistory.length) {
            this.historyIndex = this.commandHistory.length;
            this.terminalInput.value = '';
            return;
        }

        this.terminalInput.value = this.commandHistory[this.historyIndex];
    }

    appendTerminalOutput(text, className = '') {
        const span = document.createElement('span');
        span.textContent = text;
        if (className) {
            span.className = className;
        }
        
        this.terminalOutput.appendChild(span);
        this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
    }

    clearTerminal() {
        this.terminalOutput.innerHTML = '';
        const timestamp = new Date().toLocaleTimeString();
        this.appendTerminalOutput(`[${timestamp}] Terminal cleared\n`, 'info');
    }

    copyTerminal() {
        const text = this.terminalOutput.textContent;
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Terminal output copied to clipboard', 'success');
        }).catch(() => {
            this.showNotification('Failed to copy to clipboard', 'error');
        });
    }

    saveOutput() {
        const text = this.terminalOutput.textContent;
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `terminal_output_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        this.showNotification('Terminal output saved', 'success');
    }
    
    // Pagination methods (exactly like Putty_own.py)
    togglePagination() {
        this.paginationEnabled = this.autoPaginationCheckbox.checked;
        if (this.paginationEnabled) {
            this.sendSpaceBtn.disabled = true;
            this.appendTerminalOutput(`\n[${new Date().toLocaleTimeString()}] Auto-pagination: ON\n`, 'info');
        } else {
            this.appendTerminalOutput(`\n[${new Date().toLocaleTimeString()}] Auto-pagination: OFF\n`, 'info');
        }
    }
    
    sendSpace(showMessage = true) {
        if (!this.isConnected) return;
        
        // Send space via WebSocket
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'command',
                command: ' '
            }));
        }
        
        if (showMessage) {
            this.appendTerminalOutput('[SENT SPACE for pagination]\n', 'info');
        }
    }

    saveSession() {
        const sessionData = {
            host: this.hostInput.value,
            port: this.portInput.value,
            username: this.usernameInput.value,
            savedAt: new Date().toISOString()
        };
        
        localStorage.setItem('ssh_session', JSON.stringify(sessionData));
        this.showNotification('Session saved successfully', 'success');
    }

    loadSession() {
        const saved = localStorage.getItem('ssh_session');
        if (saved) {
            try {
                const sessionData = JSON.parse(saved);
                this.hostInput.value = sessionData.host || '';
                this.portInput.value = sessionData.port || '22';
                this.usernameInput.value = sessionData.username || '';
                this.showNotification('Session loaded successfully', 'success');
            } catch (error) {
                this.showNotification('Failed to load session', 'error');
            }
        } else {
            this.showNotification('No saved session found', 'info');
        }
    }

    loadSavedSession() {
        // Auto-load saved session on page load
        const saved = localStorage.getItem('ssh_session');
        if (saved) {
            try {
                const sessionData = JSON.parse(saved);
                this.hostInput.value = sessionData.host || '192.168.1.1';
                this.portInput.value = sessionData.port || '22';
                this.usernameInput.value = sessionData.username || 'admin';
            } catch (error) {
                console.log('No valid saved session found');
            }
        }
    }

    updateConnectionUI(connected) {
        this.connectBtn.disabled = connected;
        this.disconnectBtn.disabled = !connected;
        this.terminalInput.disabled = !connected;
        this.sendBtn.disabled = !connected;
        
        this.commandButtons.forEach(btn => {
            btn.disabled = !connected;
        });

        if (connected) {
            this.terminalInput.focus();
        }
    }

    updateStatus(status, text) {
        this.statusDot.className = `status-dot ${status}`;
        this.statusText.textContent = text;
    }

    showLoading(show) {
        if (show) {
            this.loadingOverlay.classList.remove('hidden');
        } else {
            this.loadingOverlay.classList.add('hidden');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '15px 20px',
            borderRadius: '10px',
            color: 'white',
            fontWeight: '500',
            zIndex: '1001',
            opacity: '0',
            transform: 'translateX(100%)',
            transition: 'all 0.3s ease'
        });

        // Set background color based on type
        const colors = {
            success: 'linear-gradient(45deg, #10b981, #059669)',
            error: 'linear-gradient(45deg, #ef4444, #dc2626)',
            info: 'linear-gradient(45deg, #3b82f6, #2563eb)',
            warning: 'linear-gradient(45deg, #f59e0b, #d97706)'
        };
        notification.style.background = colors[type] || colors.info;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
    
    // Configuration Upload Methods
    switchTab(tabName) {
        // Update button states
        this.tabBtns.forEach(btn => {
            if (btn.getAttribute('data-tab') === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        // Update content visibility
        this.tabContents.forEach(content => {
            if (content.id === tabName) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });
    }
    
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.displayFileInfo(file);
            this.uploadBtn.disabled = false;
        }
    }
    
    handleDragOver(event) {
        event.preventDefault();
        this.uploadArea.classList.add('dragover');
    }
    
    handleDragLeave(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }
    
    handleFileDrop(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'text/plain' || file.name.endsWith('.cfg') || file.name.endsWith('.conf') || file.name.endsWith('.config')) {
                this.configFileInput.files = files;
                this.displayFileInfo(file);
                this.uploadBtn.disabled = false;
            } else {
                this.showNotification('Please upload a valid configuration file (.txt, .cfg, .conf, .config)', 'error');
            }
        }
    }
    
    displayFileInfo(file) {
        this.fileName.textContent = file.name;
        this.fileSize.textContent = this.formatFileSize(file.size);
        this.fileInfo.classList.remove('hidden');
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    clearFile() {
        this.configFileInput.value = '';
        this.fileInfo.classList.add('hidden');
        this.uploadBtn.disabled = true;
    }
    
    async uploadConfig() {
        if (!this.isConnected) {
            this.showNotification('Please connect to device first', 'error');
            return;
        }
        
        const file = this.configFileInput.files[0];
        if (!file) {
            this.showNotification('Please select a configuration file', 'error');
            return;
        }
        
        try {
            const text = await file.text();
            const commands = text.split('\n').filter(line => line.trim() && !line.trim().startsWith('!'));
            
            const applyConfig = document.getElementById('apply-config').checked;
            const saveConfig = document.getElementById('save-config').checked;
            
            this.showNotification(`Uploading configuration file: ${file.name}`, 'info');
            
            // Enter configuration mode if needed
            if (applyConfig) {
                this.sendCommandToTerminal('configure terminal', false);
            }
            
            // Send each command
            for (const command of commands) {
                if (command.trim()) {
                    this.sendCommandToTerminal(command.trim(), false);
                    // Small delay between commands
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
            }
            
            // Exit configuration mode
            if (applyConfig) {
                this.sendCommandToTerminal('exit', false);
            }
            
            // Save configuration if requested
            if (saveConfig) {
                await new Promise(resolve => setTimeout(resolve, 500));
                this.sendCommandToTerminal('write memory', false);
            }
            
            this.showNotification('Configuration uploaded successfully', 'success');
            this.clearFile();
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Failed to upload configuration', 'error');
        }
    }
    
    async executeBatchCommands() {
        if (!this.isConnected) {
            this.showNotification('Please connect to device first', 'error');
            return;
        }
        
        const commandsText = this.batchCommandsText.value.trim();
        if (!commandsText) {
            this.showNotification('Please enter commands to execute', 'error');
            return;
        }
        
        const commands = commandsText.split('\n').filter(line => line.trim());
        const confirmEach = document.getElementById('confirm-each').checked;
        const showOutput = document.getElementById('show-output').checked;
        
        this.showNotification(`Executing ${commands.length} batch commands`, 'info');
        
        for (let i = 0; i < commands.length; i++) {
            const command = commands[i].trim();
            
            if (confirmEach) {
                const confirmed = confirm(`Execute command: ${command}?`);
                if (!confirmed) {
                    this.showNotification('Batch execution cancelled', 'info');
                    return;
                }
            }
            
            this.sendCommandToTerminal(command, showOutput);
            
            // Delay between commands
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        this.showNotification('Batch commands executed successfully', 'success');
    }
    
    clearBatchCommands() {
        this.batchCommandsText.value = '';
        this.showNotification('Batch commands cleared', 'info');
    }
    
    saveBatchTemplate() {
        const commandsText = this.batchCommandsText.value.trim();
        if (!commandsText) {
            this.showNotification('No commands to save', 'error');
            return;
        }
        
        const blob = new Blob([commandsText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `batch_commands_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.showNotification('Batch template saved', 'success');
    }
    
    toggleFullscreen() {
        const terminalSection = document.querySelector('.terminal-section');
        
        if (!document.fullscreenElement) {
            terminalSection.requestFullscreen().then(() => {
                this.fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i> Exit Fullscreen';
                this.showNotification('Entered fullscreen mode', 'info');
            }).catch(err => {
                console.error('Error attempting to enable fullscreen:', err);
                this.showNotification('Failed to enter fullscreen mode', 'error');
            });
        } else {
            document.exitFullscreen().then(() => {
                this.fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i> Fullscreen';
                this.showNotification('Exited fullscreen mode', 'info');
            }).catch(err => {
                console.error('Error attempting to exit fullscreen:', err);
            });
        }
    }
    
    sendCommandToTerminal(command, showInTerminal = true) {
        if (!this.isConnected) return;
        
        // Track the command to filter its echo
        this.lastSentCommand = command.trim();
        
        if (showInTerminal) {
            this.appendTerminalOutput(`\n${command}\n`, 'command');
        }
        
        // Send via WebSocket
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'command',
                command: command + '\n'
            }));
        }
    }
}

// Initialize the SSH emulator when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.sshEmulator = new SSHEmulator();
});

// Handle page unload to clean up connections
window.addEventListener('beforeunload', () => {
    if (window.sshEmulator && window.sshEmulator.isConnected) {
        window.sshEmulator.disconnect();
    }
});
