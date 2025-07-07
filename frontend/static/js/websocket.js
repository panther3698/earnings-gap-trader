/**
 * WebSocket client for real-time data streaming
 * Handles connection, reconnection, and message processing
 * Enhanced with modern features and better error handling
 */

class WebSocketClient {
    constructor(options = {}) {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
        this.reconnectDelay = options.initialReconnectDelay || 1000; // Start with 1 second
        this.maxReconnectDelay = options.maxReconnectDelay || 30000; // Max 30 seconds
        this.pingInterval = null;
        this.isConnecting = false;
        this.messageHandlers = new Map();
        this.connectionCallbacks = [];
        this.isManualClose = false;
        this.lastPingTime = null;
        this.lastPongTime = null;
        this.connectionId = null;
        this.messageQueue = [];
        this.isOnline = navigator.onLine;
        this.performanceMetrics = {
            connectTime: null,
            latency: null,
            messagesReceived: 0,
            messagesSent: 0,
            reconnections: 0
        };
        
        this.init();
    }
    
    /**
     * Initialize WebSocket connection
     */
    init() {
        this.connect();
        this.setupEventHandlers();
    }
    
    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.isConnecting || (this.socket && this.socket.readyState === WebSocket.CONNECTING)) {
            return Promise.resolve();
        }
        
        if (!this.isOnline) {
            // Cannot connect: Network is offline
            return Promise.reject(new Error('Network offline'));
        }
        
        this.isConnecting = true;
        this.isManualClose = false;
        const connectStartTime = Date.now();
        
        return new Promise((resolve, reject) => {
            try {
                // Determine WebSocket URL with connection ID
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                this.connectionId = this.generateConnectionId();
                const wsUrl = `${protocol}//${window.location.host}/ws?client_id=${this.connectionId}`;
                
                // Connecting to WebSocket
                
                this.socket = new WebSocket(wsUrl);
                this.setupSocketEventHandlers();
                
                // Set connection timeout
                const connectTimeout = setTimeout(() => {
                    if (this.socket.readyState === WebSocket.CONNECTING) {
                        this.socket.close();
                        reject(new Error('Connection timeout'));
                    }
                }, 10000); // 10 second timeout
                
                const originalOnOpen = this.socket.onopen;
                this.socket.onopen = (event) => {
                    clearTimeout(connectTimeout);
                    this.performanceMetrics.connectTime = Date.now() - connectStartTime;
                    if (originalOnOpen) originalOnOpen(event);
                    resolve();
                };
                
                const originalOnError = this.socket.onerror;
                this.socket.onerror = (error) => {
                    clearTimeout(connectTimeout);
                    if (originalOnError) originalOnError(error);
                    reject(error);
                };
                
            } catch (error) {
                // Error creating WebSocket connection
                this.isConnecting = false;
                reject(error);
            }
        });
    }
    
    /**
     * Setup WebSocket event handlers
     */
    setupSocketEventHandlers() {
        this.socket.onopen = (event) => {
            // WebSocket connected successfully
            this.isConnecting = false;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.performanceMetrics.reconnections++;
            
            // Update connection status
            this.updateConnectionStatus('connected');
            
            // Start heartbeat
            this.startHeartbeat();
            
            // Send initial subscription
            this.sendSubscription();
            
            // Process queued messages
            this.processMessageQueue();
            
            // Notify connection callbacks
            this.connectionCallbacks.forEach(callback => {
                try {
                    callback('connected', this.connectionId);
                } catch (error) {
                    // Error in connection callback
                }
            });
        };
        
        this.socket.onmessage = (event) => {
            try {
                this.performanceMetrics.messagesReceived++;
                const data = JSON.parse(event.data);
                
                // Handle pong for latency calculation
                if (data.type === 'pong' && this.lastPingTime) {
                    this.lastPongTime = Date.now();
                    this.performanceMetrics.latency = this.lastPongTime - this.lastPingTime;
                    this.updatePerformanceDisplay();
                }
                
                this.handleMessage(data);
            } catch (error) {
                // Error parsing WebSocket message
            }
        };
        
        this.socket.onclose = (event) => {
            // WebSocket connection closed
            this.isConnecting = false;
            this.stopHeartbeat();
            
            if (event.code !== 1000) { // Not a normal closure
                this.updateConnectionStatus('disconnected');
                this.scheduleReconnect();
            }
            
            // Notify connection callbacks
            this.connectionCallbacks.forEach(callback => {
                try {
                    callback('disconnected');
                } catch (error) {
                    // Error in connection callback
                }
            });
        };
        
        this.socket.onerror = (error) => {
            // WebSocket error
            this.updateConnectionStatus('error');
        };
    }
    
    /**
     * Handle incoming messages
     */
    handleMessage(data) {
        const { type, payload } = data;
        
        switch (type) {
            case 'ping':
                this.send({ type: 'pong' });
                break;
                
            case 'price_update':
                this.handlePriceUpdate(payload);
                break;
                
            case 'gap_alert':
                this.handleGapAlert(payload);
                break;
                
            case 'trade_update':
                this.handleTradeUpdate(payload);
                break;
                
            case 'portfolio_update':
                this.handlePortfolioUpdate(payload);
                break;
                
            case 'system_alert':
                this.handleSystemAlert(payload);
                break;
                
            case 'scanner_update':
                this.handleScannerUpdate(payload);
                break;
                
            default:
                // Check custom handlers
                if (this.messageHandlers.has(type)) {
                    const handler = this.messageHandlers.get(type);
                    try {
                        handler(payload);
                    } catch (error) {
                        // Error in custom handler
                    }
                } else {
                    // Unknown message type
                }
        }
    }
    
    /**
     * Handle price updates
     */
    handlePriceUpdate(payload) {
        const { symbol, price, change, change_percent } = payload;
        
        // Update price in positions table
        this.updatePositionPrice(symbol, price, change);
        
        // Update any price displays
        this.updatePriceDisplays(symbol, price, change_percent);
        
        // Price update received
    }
    
    /**
     * Handle gap alerts
     */
    handleGapAlert(payload) {
        const { symbol, gap_percent, price, company_name } = payload;
        
        // Add to gaps table
        if (window.dashboardFunctions && window.dashboardFunctions.addNewGapToTable) {
            window.dashboardFunctions.addNewGapToTable({
                symbol,
                company: company_name || symbol,
                gap_percent,
                price,
                volume: 'Live',
                detected: new Date().toLocaleTimeString()
            });
        }
        
        // Show notification
        const message = `Gap Alert: ${symbol} ${gap_percent >= 0 ? '+' : ''}${gap_percent.toFixed(1)}%`;
        this.showNotification(message, 'info');
        
        // Gap alert received
    }
    
    /**
     * Handle trade updates
     */
    handleTradeUpdate(payload) {
        const { trade_id, symbol, status, pnl, action } = payload;
        
        let message = '';
        let type = 'info';
        
        switch (action) {
            case 'opened':
                message = `Trade opened: ${symbol}`;
                type = 'success';
                break;
            case 'closed':
                message = `Trade closed: ${symbol} - P&L: ${pnl >= 0 ? '+' : ''}₹${pnl.toFixed(2)}`;
                type = pnl >= 0 ? 'success' : 'warning';
                break;
            case 'updated':
                message = `Trade updated: ${symbol}`;
                break;
        }
        
        this.showNotification(message, type);
        
        // Refresh positions table
        if (window.dashboardFunctions && window.dashboardFunctions.refreshPositions) {
            window.dashboardFunctions.refreshPositions();
        }
        
        // Trade update received
    }
    
    /**
     * Handle portfolio updates
     */
    handlePortfolioUpdate(payload) {
        const { balance, daily_pnl, total_pnl, margin_used } = payload;
        
        // Update portfolio displays
        this.updatePortfolioDisplays({
            balance,
            daily_pnl,
            total_pnl,
            margin_used
        });
        
        // Portfolio update received
    }
    
    /**
     * Handle system alerts
     */
    handleSystemAlert(payload) {
        const { message, level, timestamp } = payload;
        
        let type = 'info';
        switch (level) {
            case 'ERROR':
                type = 'error';
                break;
            case 'WARNING':
                type = 'warning';
                break;
            case 'SUCCESS':
                type = 'success';
                break;
        }
        
        this.showNotification(message, type);
        
        // Add to alerts list
        this.addToAlertsList({
            type: level.toLowerCase(),
            message,
            time: new Date(timestamp).toLocaleTimeString(),
            severity: type
        });
        
        // System alert received
    }
    
    /**
     * Handle scanner updates
     */
    handleScannerUpdate(payload) {
        const { stocks_scanned, gaps_found, scan_time } = payload;
        
        // Update scanner statistics
        const stocksScannedElement = document.getElementById('stocks-scanned');
        if (stocksScannedElement) {
            stocksScannedElement.textContent = stocks_scanned;
        }
        
        // Scanner update received
    }
    
    /**
     * Send message to server
     */
    send(data, queueIfDisconnected = true) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            try {
                const messageWithId = {
                    ...data,
                    messageId: this.generateMessageId(),
                    timestamp: Date.now()
                };
                
                this.socket.send(JSON.stringify(messageWithId));
                this.performanceMetrics.messagesSent++;
                
                return true;
            } catch (error) {
                // Error sending message
                return false;
            }
        } else {
            if (queueIfDisconnected) {
                this.messageQueue.push(data);
                // Message queued (WebSocket not connected)
            } else {
                // WebSocket not connected, cannot send message
            }
            return false;
        }
    }
    
    /**
     * Send subscription message
     */
    sendSubscription() {
        const subscriptions = [
            'price_updates',
            'gap_alerts', 
            'trade_updates',
            'portfolio_updates',
            'system_alerts',
            'scanner_updates'
        ];
        
        this.send({
            type: 'subscribe',
            payload: { subscriptions }
        });
    }
    
    /**
     * Start heartbeat
     */
    startHeartbeat() {
        this.stopHeartbeat(); // Clear any existing interval
        
        this.pingInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.lastPingTime = Date.now();
                this.send({ type: 'ping' }, false); // Don't queue pings
            }
        }, 30000); // Send ping every 30 seconds
    }
    
    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }
    
    /**
     * Schedule reconnection
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            // Max reconnection attempts reached
            this.updateConnectionStatus('failed');
            return;
        }
        
        this.reconnectAttempts++;
        
        // Scheduling reconnection attempt
        
        setTimeout(() => {
            this.updateConnectionStatus('connecting');
            this.connect();
        }, this.reconnectDelay);
        
        // Exponential backoff
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }
    
    /**
     * Update connection status
     */
    updateConnectionStatus(status) {
        // Update UI connection indicator
        if (window.dashboardFunctions && window.dashboardFunctions.updateConnectionStatus) {
            window.dashboardFunctions.updateConnectionStatus(status);
        }
        
        // Update any connection status displays
        const connectionIndicators = document.querySelectorAll('.connection-status');
        connectionIndicators.forEach(indicator => {
            indicator.className = `connection-status ${status}`;
            
            let statusText = '';
            switch (status) {
                case 'connected':
                    statusText = 'Connected';
                    break;
                case 'connecting':
                    statusText = 'Connecting...';
                    break;
                case 'disconnected':
                    statusText = 'Disconnected';
                    break;
                case 'error':
                    statusText = 'Connection Error';
                    break;
                case 'failed':
                    statusText = 'Connection Failed';
                    break;
            }
            
            indicator.textContent = statusText;
        });
    }
    
    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            // Notification: ${type.toUpperCase()}: ${message}
        }
    }
    
    /**
     * Update position price in table
     */
    updatePositionPrice(symbol, price, change) {
        const positionsTable = document.getElementById('positions-tbody');
        if (!positionsTable) return;
        
        const rows = positionsTable.querySelectorAll('tr[data-position-id]');
        rows.forEach(row => {
            const symbolCell = row.querySelector('td:first-child strong');
            if (symbolCell && symbolCell.textContent === symbol) {
                const priceCell = row.querySelector('.data-updated');
                if (priceCell) {
                    priceCell.textContent = `₹${price.toFixed(2)}`;
                    
                    // Add visual feedback
                    if (change > 0) {
                        priceCell.classList.add('text-success');
                        priceCell.classList.remove('text-danger');
                    } else if (change < 0) {
                        priceCell.classList.add('text-danger');
                        priceCell.classList.remove('text-success');
                    }
                }
            }
        });
    }
    
    /**
     * Update price displays
     */
    updatePriceDisplays(symbol, price, changePercent) {
        // Update any price widgets or displays for this symbol
        const priceDisplays = document.querySelectorAll(`[data-symbol="${symbol}"]`);
        priceDisplays.forEach(display => {
            display.textContent = `₹${price.toFixed(2)}`;
            
            if (changePercent !== undefined) {
                display.title = `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%`;
            }
        });
    }
    
    /**
     * Update portfolio displays
     */
    updatePortfolioDisplays(data) {
        if (window.dashboardFunctions && window.dashboardFunctions.updatePortfolioDisplay) {
            window.dashboardFunctions.updatePortfolioDisplay(data);
        }
    }
    
    /**
     * Add to alerts list
     */
    addToAlertsList(alert) {
        const alertsList = document.getElementById('alerts-list');
        if (!alertsList) return;
        
        // Check if list is empty
        const emptyMessage = alertsList.querySelector('.text-muted');
        if (emptyMessage) {
            alertsList.innerHTML = '';
        }
        
        const alertElement = document.createElement('div');
        alertElement.className = `list-group-item alert-${alert.type} fade-in`;
        alertElement.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${this.getAlertIcon(alert.type)} ${alert.message}</h6>
                    <small class="text-muted">${alert.time}</small>
                </div>
                <button class="btn btn-sm btn-outline-secondary" onclick="this.parentElement.parentElement.remove()"
                        data-bs-toggle="tooltip" title="Dismiss">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        alertsList.insertBefore(alertElement, alertsList.firstChild);
        
        // Keep only last 10 alerts
        const alerts = alertsList.querySelectorAll('.list-group-item');
        if (alerts.length > 10) {
            alerts[alerts.length - 1].remove();
        }
    }
    
    /**
     * Get alert icon
     */
    getAlertIcon(type) {
        const icons = {
            gap: '<i class="fas fa-search-plus text-info"></i>',
            trade: '<i class="fas fa-exchange-alt text-success"></i>',
            risk: '<i class="fas fa-exclamation-triangle text-warning"></i>',
            error: '<i class="fas fa-times-circle text-danger"></i>',
            success: '<i class="fas fa-check-circle text-success"></i>',
            warning: '<i class="fas fa-exclamation-triangle text-warning"></i>',
            info: '<i class="fas fa-info-circle text-info"></i>'
        };
        
        return icons[type] || '<i class="fas fa-bell"></i>';
    }
    
    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Handle page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page is hidden, optionally reduce update frequency
                // Page hidden, maintaining connection
            } else {
                // Page is visible, ensure connection is active
                // Page visible, ensuring connection
                if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
                    this.connect();
                }
            }
        });
        
        // Handle online/offline events
        window.addEventListener('online', () => {
            // Network online, reconnecting WebSocket
            this.connect();
        });
        
        window.addEventListener('offline', () => {
            // Network offline
            this.updateConnectionStatus('disconnected');
        });
    }
    
    /**
     * Add message handler
     */
    addMessageHandler(type, handler) {
        this.messageHandlers.set(type, handler);
    }
    
    /**
     * Remove message handler
     */
    removeMessageHandler(type) {
        this.messageHandlers.delete(type);
    }
    
    /**
     * Add connection callback
     */
    addConnectionCallback(callback) {
        this.connectionCallbacks.push(callback);
    }
    
    /**
     * Close connection
     */
    close() {
        this.stopHeartbeat();
        
        if (this.socket) {
            this.socket.close(1000, 'Client closing');
        }
    }
    
    /**
     * Get connection state
     */
    getState() {
        if (!this.socket) return 'CLOSED';
        
        switch (this.socket.readyState) {
            case WebSocket.CONNECTING:
                return 'CONNECTING';
            case WebSocket.OPEN:
                return 'OPEN';
            case WebSocket.CLOSING:
                return 'CLOSING';
            case WebSocket.CLOSED:
                return 'CLOSED';
            default:
                return 'UNKNOWN';
        }
    }
    
    /**
     * Generate unique connection ID
     */
    generateConnectionId() {
        return 'ws_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    /**
     * Generate unique message ID
     */
    generateMessageId() {
        return 'msg_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * Process queued messages
     */
    processMessageQueue() {
        if (this.messageQueue.length > 0) {
            // Processing queued messages
            
            const queue = [...this.messageQueue];
            this.messageQueue = [];
            
            queue.forEach(message => {
                this.send(message, false);
            });
        }
    }
    
    /**
     * Update performance display
     */
    updatePerformanceDisplay() {
        // Update latency display if element exists
        const latencyElement = document.getElementById('websocket-latency');
        if (latencyElement && this.performanceMetrics.latency !== null) {
            latencyElement.textContent = `${this.performanceMetrics.latency}ms`;
            
            // Color code based on latency
            latencyElement.className = 'badge';
            if (this.performanceMetrics.latency < 100) {
                latencyElement.classList.add('bg-success');
            } else if (this.performanceMetrics.latency < 300) {
                latencyElement.classList.add('bg-warning');
            } else {
                latencyElement.classList.add('bg-danger');
            }
        }
        
        // Update message counters
        const sentElement = document.getElementById('messages-sent');
        if (sentElement) {
            sentElement.textContent = this.performanceMetrics.messagesSent;
        }
        
        const receivedElement = document.getElementById('messages-received');
        if (receivedElement) {
            receivedElement.textContent = this.performanceMetrics.messagesReceived;
        }
    }
    
    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        return {
            ...this.performanceMetrics,
            connectionState: this.getState(),
            connectionId: this.connectionId,
            queuedMessages: this.messageQueue.length,
            reconnectAttempts: this.reconnectAttempts
        };
    }
    
    /**
     * Force reconnection
     */
    forceReconnect() {
        // Forcing WebSocket reconnection
        
        this.isManualClose = false;
        
        if (this.socket) {
            this.socket.close();
        }
        
        // Reset state
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        
        // Reconnect after a short delay
        setTimeout(() => {
            this.connect().catch(error => {
                // Force reconnect failed
            });
        }, 1000);
    }
    
    /**
     * Enable/disable debug mode
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
        
        if (enabled) {
            // WebSocket debug mode enabled
            // Performance metrics available
        }
    }
}

// Global WebSocket client instance
let wsClient = null;

/**
 * Initialize WebSocket connection
 */
function initWebSocket() {
    if (wsClient) {
        wsClient.close();
    }
    
    wsClient = new WebSocketClient();
    
    // Make client available globally
    window.wsClient = wsClient;
    
    // WebSocket client initialized
}

/**
 * Send message via WebSocket
 */
function sendWebSocketMessage(type, payload) {
    if (wsClient) {
        return wsClient.send({ type, payload });
    }
    
    // WebSocket client not initialized
    return false;
}

/**
 * Add custom message handler
 */
function addWebSocketHandler(type, handler) {
    if (wsClient) {
        wsClient.addMessageHandler(type, handler);
    }
}

// Export functions for global access
window.webSocketFunctions = {
    initWebSocket,
    sendWebSocketMessage,
    addWebSocketHandler
};

// WebSocket client module loaded