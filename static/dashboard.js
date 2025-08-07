/**
 * TailSentry Dashboard JavaScript
 * Handles WebSocket connectivity, real-time updates, and UI interactions
 */

document.addEventListener('DOMContentLoaded', () => {
    // Connect to WebSocket for real-time updates if on dashboard
    if (document.getElementById('dashboard-container')) {
        connectWebSocket();
    }
    
    // Setup interactive components
    setupDataRefresh();
    setupSearchFilters();
    setupDarkModeToggle();
});

// WebSocket connection
let socket;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

function connectWebSocket() {
    // Create WebSocket connection
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    
    socket = new WebSocket(wsUrl);
    
    // Connection opened
    socket.addEventListener('open', (event) => {
        console.log('WebSocket connected');
        reconnectAttempts = 0;
        showConnectedStatus(true);
    });
    
    // Listen for messages
    socket.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        updateDashboard(data);
    });
    
    // Connection closed - attempt reconnect with backoff
    socket.addEventListener('close', (event) => {
        console.log('WebSocket disconnected');
        showConnectedStatus(false);
        
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            const timeout = Math.min(1000 * (2 ** reconnectAttempts), 30000);
            reconnectAttempts++;
            
            console.log(`Attempting to reconnect in ${timeout/1000} seconds...`);
            setTimeout(connectWebSocket, timeout);
        } else {
            console.log('Maximum reconnection attempts reached. Please refresh the page.');
        }
    });
    
    // Handle errors
    socket.addEventListener('error', (event) => {
        console.error('WebSocket error:', event);
    });
}

// Update dashboard with real-time data
function updateDashboard(data) {
    if (data.type !== 'status_update') return;
    
    // Update device info
    const deviceInfo = data.device_info;
    if (deviceInfo) {
        document.getElementById('device-hostname').textContent = deviceInfo.hostname || 'N/A';
        document.getElementById('device-ip').textContent = deviceInfo.tailscale?.ip || 'N/A';
        
        // Update role display
        const roles = [];
        if (deviceInfo.tailscale?.is_exit_node) roles.push('Exit Node');
        if (deviceInfo.tailscale?.is_subnet_router) roles.push('Subnet Router');
        document.getElementById('device-role').textContent = roles.length ? roles.join(', ') : 'None';
        
        // Update network stats with formatting
        const formatBytes = (bytes) => {
            if (bytes < 1024) return `${bytes} B`;
            if (bytes < 1048576) return `${(bytes/1024).toFixed(2)} KB`;
            if (bytes < 1073741824) return `${(bytes/1048576).toFixed(2)} MB`;
            return `${(bytes/1073741824).toFixed(2)} GB`;
        };
        
        const txBytes = deviceInfo.tailscale?.tx_bytes || 0;
        const rxBytes = deviceInfo.tailscale?.rx_bytes || 0;
        document.getElementById('tx-bytes').textContent = formatBytes(txBytes);
        document.getElementById('rx-bytes').textContent = formatBytes(rxBytes);
        
        // Update peers count
        document.getElementById('peers-count').textContent = data.peers_count || 0;
    }
    
    // Update timestamp
    const timestamp = new Date(data.timestamp * 1000).toLocaleTimeString();
    document.getElementById('last-update').textContent = timestamp;
}

// Show connection status
function showConnectedStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) return;
    
    if (connected) {
        statusElement.textContent = 'Connected';
        statusElement.className = 'text-green-500';
    } else {
        statusElement.textContent = 'Disconnected';
        statusElement.className = 'text-red-500';
    }
}

// Setup data refresh buttons
function setupDataRefresh() {
    const refreshBtn = document.getElementById('refresh-data');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            // Visual feedback
            refreshBtn.classList.add('animate-spin');
            setTimeout(() => refreshBtn.classList.remove('animate-spin'), 1000);
            
            // Fetch fresh data or reconnect WebSocket if needed
            if (socket && socket.readyState !== WebSocket.OPEN) {
                connectWebSocket();
            }
            
            // For non-WebSocket pages, reload the page
            if (!socket) {
                window.location.reload();
            }
        });
    }
}

// Setup search and filters for tables
function setupSearchFilters() {
    const searchInput = document.getElementById('peer-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const peerRows = document.querySelectorAll('#peers-table tbody tr');
            
            peerRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }
}

// Setup dark mode toggle
function setupDarkModeToggle() {
    const darkModeBtn = document.getElementById('dark-mode-toggle');
    if (darkModeBtn) {
        // Check for saved preference
        const savedMode = localStorage.getItem('darkMode');
        if (savedMode === 'true') {
            document.documentElement.classList.add('dark');
        }
        
        darkModeBtn.addEventListener('click', () => {
            document.documentElement.classList.toggle('dark');
            localStorage.setItem(
                'darkMode', 
                document.documentElement.classList.contains('dark')
            );
        });
    }
}
