/**
 * Main Dashboard JavaScript for Earnings Gap Trader
 * Handles real-time data updates, charts, and user interactions
 */

// Global variables
let pnlChart = null;
let volumeChart = null;
let autoRefreshInterval = null;
let isAutoRefreshEnabled = true;
let currentTradingMode = 'AUTO';
let lastDataUpdate = null;
let performanceMetrics = {
    totalTrades: 0,
    winningTrades: 0,
    losingTrades: 0,
    totalPnL: 0,
    dailyPnL: 0,
    avgWin: 0,
    avgLoss: 0,
    maxDrawdown: 0,
    sharpeRatio: 0
};

// Dashboard initialization
document.addEventListener('DOMContentLoaded', function() {
    // Dashboard initialization started
    
    initializeDashboard();
    setupEventListeners();
    startDataRefresh();
});

/**
 * Initialize all dashboard components
 */
function initializeDashboard() {
    // Initializing dashboard components
    
    try {
        // Initialize charts
        initializePnLChart();
        initializeVolumeChart();
        
        // Initialize WebSocket if available
        if (typeof initWebSocket === 'function') {
            initWebSocket();
            setupWebSocketHandlers();
        }
        
        // Load initial data
        loadInitialData();
        
        // Setup auto-refresh
        setupAutoRefresh();
        
        // Initialize tooltips and popovers
        initializeBootstrapComponents();
        
        // Dashboard initialization complete
        
    } catch (error) {
        // Dashboard initialization failed - error logged to server
        showNotification('Failed to initialize dashboard', 'error');
    }
}

/**
 * Initialize P&L Chart with Chart.js
 */
function initializePnLChart() {
    const ctx = document.getElementById('pnlChart');
    if (!ctx) {
        // P&L chart canvas not found
        return;
    }
    
    const chartCtx = ctx.getContext('2d');
    
    pnlChart = new Chart(chartCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Cumulative P&L',
                data: [],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 6
            }, {
                label: 'Daily P&L',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 1,
                fill: false,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#64748b'
                    }
                },
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#64748b',
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            return `${label}: ${formatCurrency(context.parsed.y)}`;
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#64748b',
                        usePointStyle: true
                    }
                }
            },
            animation: {
                duration: 750,
                easing: 'easeInOutQuart'
            }
        }
    });
    
    // P&L chart initialized
}

/**
 * Initialize Volume Chart
 */
function initializeVolumeChart() {
    const ctx = document.getElementById('volumeChart');
    if (!ctx) return;
    
    const chartCtx = ctx.getContext('2d');
    
    volumeChart = new Chart(chartCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Trading Volume',
                data: [],
                backgroundColor: 'rgba(59, 130, 246, 0.6)',
                borderColor: '#3b82f6',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
    
    // Volume chart initialized
}

/**
 * Setup WebSocket message handlers
 */
function setupWebSocketHandlers() {
    if (typeof wsClient === 'undefined') {
        // WebSocket client not available
        return;
    }
    
    // Add custom handlers for dashboard-specific messages
    wsClient.addMessageHandler('pnl_update', handlePnLUpdate);
    wsClient.addMessageHandler('position_update', handlePositionUpdate);
    wsClient.addMessageHandler('signal_alert', handleSignalAlert);
    wsClient.addMessageHandler('trade_update', handleTradeUpdate);
    wsClient.addMessageHandler('system_status', handleSystemStatus);
    wsClient.addMessageHandler('risk_alert', handleRiskAlert);
    wsClient.addMessageHandler('scanner_update', handleScannerUpdate);
    
    // Connection status updates
    wsClient.addConnectionCallback((status, connectionId) => {
        updateConnectionStatus(status);
        if (status === 'connected') {
            requestInitialData();
        }
    });
    
    // WebSocket handlers configured
}

/**
 * Handle P&L updates from WebSocket
 */
function handlePnLUpdate(data) {
    // P&L Update received
    
    const { total_pnl, daily_pnl, unrealized_pnl, realized_pnl, timestamp } = data;
    
    // Update metric cards
    updateMetricCard('totalPnL', total_pnl);
    updateMetricCard('todayPnL', daily_pnl);
    updateMetricCard('unrealizedPnL', unrealized_pnl);
    updateMetricCard('realizedPnL', realized_pnl);
    
    // Update chart
    updatePnLChart(data);
    
    // Update performance metrics
    performanceMetrics.totalPnL = total_pnl;
    performanceMetrics.dailyPnL = daily_pnl;
    
    // Visual feedback
    animateMetricUpdate('totalPnL');
    
    lastDataUpdate = new Date();
}

/**
 * Handle position updates
 */
function handlePositionUpdate(data) {
    // Position Update received
    
    const { positions, active_count, total_value } = data;
    
    // Update positions table
    updatePositionsTable(positions);
    
    // Update active positions count
    updateMetricCard('activePositions', active_count);
    
    // Update total portfolio value if provided
    if (total_value !== undefined) {
        updateMetricCard('portfolioValue', total_value);
    }
}

/**
 * Handle new signal alerts
 */
function handleSignalAlert(data) {
    // Signal Alert received
    
    const { signal, confidence, symbol, gap_percent, signal_type } = data;
    
    // Add to signals feed
    addSignalToFeed(data);
    
    // Update signals count
    incrementSignalsCount();
    
    // Show notification
    const message = `New ${signal_type}: ${symbol} (${gap_percent >= 0 ? '+' : ''}${gap_percent.toFixed(1)}%)`;
    showNotification(message, 'info');
    
    // Show approval modal if in manual mode
    if (currentTradingMode === 'MANUAL') {
        showSignalApprovalModal(data);
    }
    
    // Play notification sound if enabled
    playNotificationSound('signal');
}

/**
 * Handle trade updates
 */
function handleTradeUpdate(data) {
    // Trade Update received
    
    const { action, symbol, pnl, status } = data;
    
    let message = '';
    let type = 'info';
    
    switch (action) {
        case 'opened':
            message = `Trade opened: ${symbol}`;
            type = 'success';
            break;
        case 'closed':
            message = `Trade closed: ${symbol} - P&L: ${formatCurrency(pnl)}`;
            type = pnl >= 0 ? 'success' : 'warning';
            updateTradeStatistics(pnl);
            break;
        case 'modified':
            message = `Trade modified: ${symbol}`;
            type = 'info';
            break;
    }
    
    showNotification(message, type);
    
    // Update positions display
    if (action === 'opened' || action === 'closed') {
        refreshPositions();
    }
    
    // Play notification sound
    playNotificationSound(action === 'closed' && pnl > 0 ? 'profit' : 'trade');
}

/**
 * Handle system status updates
 */
function handleSystemStatus(data) {
    // System Status received
    
    const { trading_mode, is_paused, emergency_stop, system_health } = data;
    
    // Update trading mode
    if (trading_mode) {
        currentTradingMode = trading_mode;
        updateTradingModeDisplay(trading_mode);
    }
    
    // Update system status indicators
    updateSystemStatusIndicators({
        is_paused,
        emergency_stop,
        system_health
    });
    
    // Update component health
    if (data.component_health) {
        updateComponentHealth(data.component_health);
    }
}

/**
 * Handle risk alerts
 */
function handleRiskAlert(data) {
    // Risk Alert received
    
    const { message, severity, risk_type } = data;
    
    // Show prominent notification
    showNotification(message, severity.toLowerCase());
    
    // Add to risk monitor
    addRiskAlert(data);
    
    // Play warning sound for high severity
    if (severity === 'HIGH') {
        playNotificationSound('warning');
    }
}

/**
 * Handle scanner updates
 */
function handleScannerUpdate(data) {
    // Scanner Update received
    
    const { stocks_scanned, gaps_found, scan_time, recent_gaps } = data;
    
    // Update scanner statistics
    updateScannerStats({
        stocks_scanned,
        gaps_found,
        scan_time
    });
    
    // Update recent gaps table
    if (recent_gaps) {
        updateRecentGapsTable(recent_gaps);
    }
}

/**
 * Update P&L chart with new data
 */
function updatePnLChart(data) {
    if (!pnlChart) return;
    
    const now = new Date();
    const { total_pnl, daily_pnl } = data;
    
    // Add new data point
    pnlChart.data.labels.push(now);
    pnlChart.data.datasets[0].data.push(total_pnl);
    pnlChart.data.datasets[1].data.push(daily_pnl);
    
    // Keep only last 100 data points
    const maxPoints = 100;
    if (pnlChart.data.labels.length > maxPoints) {
        pnlChart.data.labels.shift();
        pnlChart.data.datasets[0].data.shift();
        pnlChart.data.datasets[1].data.shift();
    }
    
    // Update chart
    pnlChart.update('none');
}

/**
 * Update positions table
 */
function updatePositionsTable(positions) {
    const tbody = document.getElementById('positionsTableBody');
    if (!tbody) return;
    
    if (!positions || positions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted py-4">
                    <i class="fas fa-inbox fa-2x mb-2 d-block"></i>
                    No active positions
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = positions.map(position => {
        const pnlClass = getValueColorClass(position.pnl);
        const pnlPercentClass = getValueColorClass(position.pnl_percent);
        
        return `
            <tr data-position-id="${position.symbol}">
                <td>
                    <strong>${position.symbol}</strong>
                    <br>
                    <small class="text-muted">${position.company_name || ''}</small>
                </td>
                <td>
                    <span class="badge ${position.side === 'BUY' ? 'bg-success' : 'bg-danger'}">
                        ${position.side}
                    </span>
                    <br>
                    <small>${position.quantity}</small>
                </td>
                <td>
                    <span class="data-updated">${formatCurrency(position.entry_price)}</span>
                    <br>
                    <small class="text-muted">${formatTime(position.entry_time)}</small>
                </td>
                <td>
                    <span class="data-updated">${formatCurrency(position.current_price)}</span>
                    <br>
                    <small class="text-muted">${formatTime(position.last_updated)}</small>
                </td>
                <td class="${pnlClass}">
                    <strong>${position.pnl >= 0 ? '+' : ''}${formatCurrency(position.pnl)}</strong>
                    <br>
                    <small>(${position.pnl_percent >= 0 ? '+' : ''}${position.pnl_percent.toFixed(2)}%)</small>
                </td>
                <td>
                    ${formatCurrency(position.stop_loss)}
                    <br>
                    <small class="text-muted">SL</small>
                </td>
                <td>
                    ${formatCurrency(position.target)}
                    <br>
                    <small class="text-muted">TGT</small>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-warning" onclick="modifyPosition('${position.symbol}')" title="Modify">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="closePosition('${position.symbol}')" title="Close">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Add signal to live feed
 */
function addSignalToFeed(signal) {
    const feed = document.getElementById('signalsFeed');
    if (!feed) return;
    
    // Clear placeholder if exists
    const placeholder = feed.querySelector('.text-center');
    if (placeholder) {
        feed.innerHTML = '';
    }
    
    const signalElement = document.createElement('div');
    signalElement.className = 'list-group-item signal-item fade-in';
    signalElement.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <h6 class="mb-0">
                        <strong>${signal.symbol}</strong>
                        <span class="badge ${signal.signal_type === 'EARNINGS_GAP_UP' ? 'bg-success' : 'bg-danger'} ms-2">
                            ${signal.gap_percent >= 0 ? '+' : ''}${signal.gap_percent.toFixed(1)}%
                        </span>
                    </h6>
                    <small class="text-muted">${formatTime(new Date())}</small>
                </div>
                <p class="mb-1">
                    <span class="badge bg-secondary me-1">
                        ${signal.confidence} (${signal.confidence_score}%)
                    </span>
                    <span class="badge bg-info">
                        Vol: ${signal.volume_ratio.toFixed(1)}x
                    </span>
                </p>
                <small class="text-muted">
                    Entry: ${formatCurrency(signal.entry_price)} | 
                    Target: ${formatCurrency(signal.profit_target)} |
                    SL: ${formatCurrency(signal.stop_loss)}
                </small>
            </div>
            <div class="ms-2">
                ${currentTradingMode === 'MANUAL' ? 
                    `<button class="btn btn-sm btn-outline-primary" onclick="showSignalDetails('${signal.signal_id}')">
                        <i class="fas fa-eye"></i>
                    </button>` : 
                    '<span class="badge bg-success">AUTO</span>'
                }
            </div>
        </div>
    `;
    
    feed.insertBefore(signalElement, feed.firstChild);
    
    // Keep only last 20 signals
    const items = feed.querySelectorAll('.signal-item');
    if (items.length > 20) {
        items[items.length - 1].remove();
    }
}

/**
 * Show signal approval modal
 */
function showSignalApprovalModal(signal) {
    const modal = document.getElementById('signalApprovalModal');
    if (!modal) return;
    
    // Populate modal with signal data
    document.getElementById('modalSymbol').textContent = signal.symbol;
    document.getElementById('modalCompany').textContent = signal.company_name || signal.symbol;
    document.getElementById('modalSignalType').textContent = signal.signal_type;
    document.getElementById('modalConfidence').textContent = `${signal.confidence} (${signal.confidence_score}%)`;
    document.getElementById('modalGapPercent').textContent = `${signal.gap_percent >= 0 ? '+' : ''}${signal.gap_percent.toFixed(1)}%`;
    document.getElementById('modalVolumeRatio').textContent = `${signal.volume_ratio.toFixed(1)}x`;
    document.getElementById('modalEntryPrice').textContent = formatCurrency(signal.entry_price);
    document.getElementById('modalStopLoss').textContent = formatCurrency(signal.stop_loss);
    document.getElementById('modalTarget').textContent = formatCurrency(signal.profit_target);
    document.getElementById('modalRiskReward').textContent = `1:${signal.risk_reward_ratio.toFixed(1)}`;
    
    // Set suggested position size
    const suggestedQty = Math.floor((signal.position_size || 10000) / signal.entry_price);
    document.getElementById('manualQuantity').value = suggestedQty;
    document.getElementById('manualInvestment').value = signal.position_size || 10000;
    
    // Store signal for approval actions
    window.currentSignal = signal;
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    // Auto-reject after timeout
    setTimeout(() => {
        if (window.currentSignal?.signal_id === signal.signal_id) {
            bootstrapModal.hide();
            showNotification('Signal approval timeout - automatically rejected', 'warning');
        }
    }, 300000); // 5 minutes
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Chart period toggle
    document.querySelectorAll('input[name="chartPeriod"]').forEach(radio => {
        radio.addEventListener('change', function() {
            updateChartPeriod(this.value);
        });
    });
    
    // Auto refresh toggle
    const autoRefreshBtn = document.getElementById('autoRefreshBtn');
    if (autoRefreshBtn) {
        autoRefreshBtn.addEventListener('click', toggleAutoRefresh);
    }
    
    // Manual refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshPositions);
    }
    
    // Trading mode buttons
    document.querySelectorAll('[data-trading-mode]').forEach(btn => {
        btn.addEventListener('click', function() {
            const mode = this.dataset.tradingMode;
            setTradingMode(mode);
        });
    });
    
    // Scanner controls
    const pauseScannerBtn = document.getElementById('pauseScannerBtn');
    if (pauseScannerBtn) {
        pauseScannerBtn.addEventListener('click', toggleScanner);
    }
    
    const scanNowBtn = document.getElementById('scanNowBtn');
    if (scanNowBtn) {
        scanNowBtn.addEventListener('click', scanNow);
    }
    
    // Emergency stop button
    const emergencyStopBtn = document.getElementById('emergencyStopBtn');
    if (emergencyStopBtn) {
        emergencyStopBtn.addEventListener('click', confirmEmergencyStop);
    }
    
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Window visibility change
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Event listeners configured
}

/**
 * Setup auto refresh
 */
function setupAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(() => {
        if (isAutoRefreshEnabled && !document.hidden) {
            requestCurrentData();
        }
    }, 5000); // Refresh every 5 seconds
    
    // Auto-refresh configured
}

/**
 * Initialize Bootstrap components
 */
function initializeBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Bootstrap components initialized
}

/**
 * Request initial data load
 */
function requestInitialData() {
    // Requesting initial data...
    
    if (typeof sendWebSocketMessage === 'function') {
        sendWebSocketMessage('request_status', {});
        sendWebSocketMessage('request_positions', {});
        sendWebSocketMessage('request_performance', {});
        sendWebSocketMessage('request_scanner_status', {});
    }
}

/**
 * Request current data update
 */
function requestCurrentData() {
    if (typeof sendWebSocketMessage === 'function') {
        sendWebSocketMessage('request_realtime_data', {
            timestamp: Date.now()
        });
    }
}

/**
 * Load initial data via API
 */
async function loadInitialData() {
    try {
        showLoading();
        
        // Load dashboard data
        const response = await fetch('/api/dashboard-data');
        const data = await response.json();
        
        if (data.success) {
            // Update metrics
            updateDashboardMetrics(data.metrics);
            
            // Update positions
            if (data.positions) {
                updatePositionsTable(data.positions);
            }
            
            // Update chart data
            if (data.chart_data) {
                updateChartsWithHistoricalData(data.chart_data);
            }
            
            // Initial data loaded
        }
        
    } catch (error) {
        // Failed to load initial data
        showNotification('Failed to load dashboard data', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Start data refresh cycle
 */
function startDataRefresh() {
    // Request initial data
    requestInitialData();
    
    // Start auto-refresh if WebSocket is not available
    if (typeof wsClient === 'undefined') {
        setupAutoRefresh();
    }
}

/**
 * Update dashboard metrics
 */
function updateDashboardMetrics(metrics) {
    Object.entries(metrics).forEach(([key, value]) => {
        updateMetricCard(key, value);
    });
}

/**
 * Update metric card value
 */
function updateMetricCard(elementId, value) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Format value based on type
    let formattedValue;
    if (typeof value === 'number') {
        if (elementId.toLowerCase().includes('pnl') || elementId.toLowerCase().includes('value')) {
            formattedValue = formatCurrency(value);
        } else if (elementId.toLowerCase().includes('rate') || elementId.toLowerCase().includes('percent')) {
            formattedValue = formatPercentage(value);
        } else {
            formattedValue = formatNumber(value);
        }
    } else {
        formattedValue = value;
    }
    
    element.textContent = formattedValue;
    
    // Update color class for P&L values
    if (elementId.toLowerCase().includes('pnl') && typeof value === 'number') {
        element.className = `metric-value ${getValueColorClass(value)}`;
    }
}

/**
 * Animate metric update
 */
function animateMetricUpdate(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.classList.add('data-pulse');
    setTimeout(() => {
        element.classList.remove('data-pulse');
    }, 1500);
}

/**
 * Global action functions for dashboard controls
 */

// Toggle auto refresh
function toggleAutoRefresh() {
    isAutoRefreshEnabled = !isAutoRefreshEnabled;
    const btn = document.getElementById('autoRefreshBtn');
    
    if (isAutoRefreshEnabled) {
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-outline-success');
        btn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Auto Refresh';
        showNotification('Auto refresh enabled', 'success');
    } else {
        btn.classList.remove('btn-outline-success');
        btn.classList.add('btn-outline-secondary');
        btn.innerHTML = '<i class="fas fa-pause me-1"></i>Paused';
        showNotification('Auto refresh paused', 'info');
    }
}

// Refresh positions manually
async function refreshPositions() {
    try {
        showLoading();
        
        const response = await fetch('/api/positions');
        const data = await response.json();
        
        if (data.success) {
            updatePositionsTable(data.positions);
            showNotification('Positions refreshed', 'success');
        } else {
            showNotification('Failed to refresh positions', 'error');
        }
        
    } catch (error) {
        // Error refreshing positions
        showNotification('Error refreshing positions', 'error');
    } finally {
        hideLoading();
    }
}

// Close position
async function closePosition(symbol) {
    if (!confirm(`Are you sure you want to close the ${symbol} position?`)) {
        return;
    }
    
    try {
        showLoading();
        
        const response = await fetch('/api/close-position', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbol })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`${symbol} position closed successfully`, 'success');
            refreshPositions();
        } else {
            showNotification(`Failed to close ${symbol}: ${data.error}`, 'error');
        }
        
    } catch (error) {
        // Error closing position
        showNotification('Error closing position', 'error');
    } finally {
        hideLoading();
    }
}

// Modify position
function modifyPosition(symbol) {
    // Implementation for position modification
    showNotification('Position modification feature coming soon', 'info');
}

// Set trading mode
async function setTradingMode(mode) {
    try {
        const response = await fetch('/api/set-trading-mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mode })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentTradingMode = mode;
            updateTradingModeDisplay(mode);
            showNotification(`Trading mode set to ${mode}`, 'success');
        } else {
            showNotification('Failed to set trading mode', 'error');
        }
        
    } catch (error) {
        // Error setting trading mode
        showNotification('Error setting trading mode', 'error');
    }
}

// Toggle scanner
async function toggleScanner() {
    try {
        const response = await fetch('/api/toggle-scanner', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            const statusElement = document.getElementById('scannerStatus');
            const btnElement = document.getElementById('pauseScannerBtn');
            
            if (data.status === 'active') {
                statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Active';
                statusElement.className = 'badge bg-success';
                btnElement.innerHTML = '<i class="fas fa-pause me-1"></i>Pause';
                showNotification('Scanner resumed', 'success');
            } else {
                statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Paused';
                statusElement.className = 'badge bg-warning';
                btnElement.innerHTML = '<i class="fas fa-play me-1"></i>Resume';
                showNotification('Scanner paused', 'warning');
            }
        } else {
            showNotification('Failed to toggle scanner', 'error');
        }
        
    } catch (error) {
        // Error toggling scanner
        showNotification('Error toggling scanner', 'error');
    }
}

// Scan now
async function scanNow() {
    try {
        showLoading();
        
        const response = await fetch('/api/scan-now', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Manual scan initiated', 'success');
            document.getElementById('lastScanTime').textContent = new Date().toLocaleTimeString();
        } else {
            showNotification('Failed to initiate scan', 'error');
        }
        
    } catch (error) {
        // Error initiating scan
        showNotification('Error initiating scan', 'error');
    } finally {
        hideLoading();
    }
}

// Emergency stop
function confirmEmergencyStop() {
    const modal = document.getElementById('emergencyStopModal');
    if (modal) {
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
}

// Execute emergency stop
async function executeEmergencyStop() {
    try {
        showLoading();
        
        const response = await fetch('/api/emergency-stop', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Emergency stop executed', 'warning');
            // Hide modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('emergencyStopModal'));
            if (modal) modal.hide();
        } else {
            showNotification('Failed to execute emergency stop', 'error');
        }
        
    } catch (error) {
        // Error executing emergency stop
        showNotification('Error executing emergency stop', 'error');
    } finally {
        hideLoading();
    }
}

// Approve signal
async function approveSignal() {
    if (!window.currentSignal) return;
    
    const quantity = parseInt(document.getElementById('manualQuantity').value);
    const investment = parseFloat(document.getElementById('manualInvestment').value);
    
    try {
        showLoading();
        
        const response = await fetch('/api/approve-signal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                signal_id: window.currentSignal.signal_id,
                quantity,
                investment,
                action: 'approve'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Signal approved and executed', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('signalApprovalModal'));
            if (modal) modal.hide();
            refreshPositions();
        } else {
            showNotification(`Failed to approve signal: ${data.error}`, 'error');
        }
        
    } catch (error) {
        // Error approving signal
        showNotification('Error approving signal', 'error');
    } finally {
        hideLoading();
    }
}

// Utility functions
function updateTradingModeDisplay(mode) {
    const element = document.getElementById('tradingModeDisplay');
    if (element) {
        element.textContent = mode;
        element.className = `badge ${mode === 'AUTO' ? 'bg-success' : mode === 'MANUAL' ? 'bg-warning' : 'bg-secondary'}`;
    }
}

function updateConnectionStatus(status) {
    const elements = document.querySelectorAll('.connection-status');
    elements.forEach(element => {
        element.textContent = status.toUpperCase();
        element.className = `connection-status connection-${status}`;
    });
}

function incrementSignalsCount() {
    const element = document.getElementById('signalsToday');
    if (element) {
        const current = parseInt(element.textContent) || 0;
        element.textContent = current + 1;
    }
}

function updateTradeStatistics(pnl) {
    performanceMetrics.totalTrades++;
    
    if (pnl > 0) {
        performanceMetrics.winningTrades++;
    } else if (pnl < 0) {
        performanceMetrics.losingTrades++;
    }
    
    // Update win rate
    const winRate = (performanceMetrics.winningTrades / performanceMetrics.totalTrades) * 100;
    updateMetricCard('winRate', winRate);
    updateMetricCard('totalTrades', performanceMetrics.totalTrades);
}

function handleVisibilityChange() {
    if (document.hidden) {
        // Page is hidden, reduce update frequency
        // Dashboard hidden, reducing update frequency
    } else {
        // Page is visible, resume normal updates
        // Dashboard visible, resuming normal updates
        requestCurrentData();
    }
}

function playNotificationSound(type) {
    // Implementation for audio notifications
    // Can be enhanced with different sounds for different events
    if ('Audio' in window) {
        try {
            const audio = new Audio(`/static/sounds/${type}.mp3`);
            audio.volume = 0.3;
            audio.play().catch(e => {/* Audio play failed */});
        } catch (e) {
            // Audio not available
        }
    }
}

// Export dashboard functions for global access
window.dashboardFunctions = {
    updatePnLMetrics: handlePnLUpdate,
    updatePositionsTable,
    updateConnectionStatus,
    refreshPositions,
    addSignalToFeed,
    updatePortfolioDisplay: updateDashboardMetrics,
    addNewGapToTable: (gap) => {
        // Implementation for adding gaps to recent gaps table
        // New gap detected
    }
};

// Dashboard JavaScript loaded and ready