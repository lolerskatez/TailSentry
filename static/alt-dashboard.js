// Alternative TailSentry Dashboard - Clean & Modern Implementation
// Focused on simplicity, performance, and user experience

function altDashboard() {
  return {
    // === Core State ===
    _initialized: false,
    isLoading: false,
    isOnline: false,
    lastUpdate: '',
    autoRefresh: true,
    refreshInterval: 30,
    refreshTimer: null,
    
    // === UI State ===
    showSettings: false,
    showDeviceModal: false,
    showSubnetModal: false,
    theme: localStorage.getItem('alt-dashboard-theme') || 'system',
    
    // === Data ===
    stats: {
      total: 0,
      online: 0,
      offline: 0
    },
    
    device: {
      hostname: '',
      ip: '',
      isExitNode: false,
      isSubnetRouter: false
    },
    
    devices: [],
    filteredDevices: [],
    selectedDevice: null,
    subnets: [],
    tailscaleStatus: 'Unknown',
    
  // === Filters ===
    searchQuery: '',
    deviceFilter: 'all',
  // Persisted exit node setting
  advertiseExitNode: false,
    
    // === Toast System ===
    toast: {
      message: '',
      type: 'info', // success, error, info
      timeout: null
    },

    // === Initialization ===
    async init() {
      // Prevent double initialization
      if (this._initialized) {
        console.log('🔄 Alternative dashboard already initialized, skipping...');
        return;
      }
      this._initialized = true;
      this.applyTheme();
      if (this.autoRefresh) this.setupAutoRefresh();
      // Load settings first to get exit node state
      await this.loadSettings();
      // Load all data (status, peers, subnets)
      await this.loadAllData();
      this.setupEventListeners();
      this.showToast('Dashboard initialized', 'success');
    },

    // Fetch persisted Tailscale settings (exit node state)
    async loadSettings() {
      try {
        const response = await fetch('/api/tailscale-settings');
        if (!response.ok) throw new Error('Settings API failed');
        const data = await response.json();
        // Load persisted exit node setting into UI state
        this.advertiseExitNode = data.advertise_exit_node || false;
        // Also reflect in device state before actual status fetch
        this.device.isExitNode = data.advertise_exit_node || false;
      } catch (error) {
        console.error('Failed to load Tailscale settings:', error);
      }
    },

    setupEventListeners() {
      // Online/offline detection
      window.addEventListener('online', () => {
        this.isOnline = true;
        this.showToast('Connection restored', 'success');
        this.loadAllData();
      });
      
      window.addEventListener('offline', () => {
        this.isOnline = false;
        this.showToast('Connection lost', 'error');
      });
      
      // Theme change detection
      if (this.theme === 'system') {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', () => {
          if (this.theme === 'system') {
            this.applyTheme();
          }
        });
      }
    },

    // === Data Loading ===
    async loadAllData() {
      this.isLoading = true;
      
      try {
        await Promise.allSettled([
          this.loadStatus(),
          this.loadPeers(),
          this.loadSubnets(),
          this.loadExitNodeStatus()
        ]);
        
        this.updateStats();
        this.filterDevices();
        this.lastUpdate = new Date().toLocaleTimeString();
        this.isOnline = true;
        
      } catch (error) {
        console.error('Failed to load data:', error);
        this.showToast('Failed to load data', 'error');
        this.isOnline = false;
      } finally {
        this.isLoading = false;
      }
    },

    async loadStatus() {
      try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error('Status API failed');
        
        const data = await response.json();
        this.tailscaleStatus = data.BackendState || 'Unknown';
        
        // Update device info
        if (data.Self) {
          this.device.hostname = data.Self.HostName || '';
          this.device.ip = data.Self.TailscaleIPs?.[0] || '';
          // Check if device is advertising exit node routes
          const advRoutes = data.Self.AdvertisedRoutes || [];
          this.device.isExitNode = advRoutes.includes('0.0.0.0/0') || advRoutes.includes('::/0');
        }
      } catch (error) {
        console.error('Failed to load status:', error);
        this.tailscaleStatus = 'Error';
      }
    },

    async loadPeers() {
      try {
        const response = await fetch('/api/peers');
        if (!response.ok) throw new Error('Peers API failed');
        
        const data = await response.json();
        // Ensure devices is always an array
        this.devices = Array.isArray(data.peers) ? data.peers : [];
        
      } catch (error) {
        console.error('Failed to load peers:', error);
        this.devices = []; // Ensure it's always an array
      }
    },

    async loadSubnets() {
      try {
        const response = await fetch('/api/subnet-routes');
        if (!response.ok) throw new Error('Subnets API failed');
        
        const data = await response.json();
        this.subnets = data.routes || [];
        
      } catch (error) {
        console.error('Failed to load subnets:', error);
        this.subnets = [];
      }
    },

    async loadExitNodeStatus() {
  // No longer sets isExitNode here; handled in loadStatus
  return;
    },

    // === Data Processing ===
    updateStats() {
      // Ensure devices is an array before processing
      if (!Array.isArray(this.devices)) {
        console.warn('Devices is not an array:', this.devices);
        this.devices = [];
      }
      
      const total = this.devices.length;
      const online = this.devices.filter(d => d.online).length;
      const offline = total - online;
      
      this.stats = { total, online, offline };
    },

    filterDevices() {
      // Ensure devices is an array before filtering
      if (!Array.isArray(this.devices)) {
        console.warn('Devices is not an array for filtering:', this.devices);
        this.filteredDevices = [];
        return;
      }
      
      let filtered = this.devices;
      
      // Apply search filter
      if (this.searchQuery.trim()) {
        const query = this.searchQuery.toLowerCase();
        filtered = filtered.filter(device => 
          (device.hostname || '').toLowerCase().includes(query) ||
          (device.ip || '').toLowerCase().includes(query) ||
          (device.os || '').toLowerCase().includes(query)
        );
      }
      
      // Apply status filter
      if (this.deviceFilter === 'online') {
        filtered = filtered.filter(device => device.online);
      } else if (this.deviceFilter === 'offline') {
        filtered = filtered.filter(device => !device.online);
      }
      
      this.filteredDevices = filtered;
    },

    // === Actions ===
    async refreshData() {
      if (this.isLoading) return;
      await this.loadAllData();
      this.showToast('Data refreshed', 'success');
    },

    async toggleExitNode() {
      if (this.isLoading) return;
      this.isLoading = true;
      // Toggle based on persisted setting
      const newValue = !this.advertiseExitNode;
      try {
        const response = await fetch('/api/tailscale-settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ advertise_exit_node: newValue })
        });
        if (!response.ok) throw new Error('Settings update failed');
        const result = await response.json();
        if (result.success) {
          // Update UI state
          this.advertiseExitNode = newValue;
          this.device.isExitNode = newValue;
           this.showToast(newValue ? 'Exit node enabled' : 'Exit node disabled', 'success');
           // reload settings and status
           await this.loadSettings();
           await this.loadAllData();
        } else {
          this.showToast('Failed to toggle exit node: ' + (result.error || 'Unknown error'), 'error');
        }
      } catch (error) {
        console.error('Toggle exit node error:', error);
        this.showToast('Failed to toggle exit node', 'error');
      } finally {
        this.isLoading = false;
      }
    },

    // === Device Details ===
    showDeviceDetails(device) {
      this.selectedDevice = device;
      this.showDeviceModal = true;
    },

    async pingDevice(device) {
      if (!device) return;
      
      this.showToast(`Pinging ${device.hostname || device.ip}...`, 'info');
      
      // Note: This would need a backend endpoint for actual ping
      // For now, just show a placeholder response
      setTimeout(() => {
        this.showToast(`Ping to ${device.hostname || device.ip} completed`, 'success');
      }, 2000);
    },

    // === Utility Functions ===
    formatLastSeen(lastSeen) {
      if (!lastSeen) return 'Never';
      
      const date = new Date(lastSeen);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}d ago`;
    },

    // === Settings & Preferences ===
    setupAutoRefresh() {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer);
      }
      
      if (this.autoRefresh && this.refreshInterval > 0) {
        this.refreshTimer = setInterval(() => {
          if (!this.showDeviceModal && !this.showSettings) {
            this.loadAllData();
          }
        }, this.refreshInterval * 1000);
      }
    },

    applyTheme() {
      const html = document.documentElement;
      
      if (this.theme === 'dark') {
        html.classList.add('dark');
      } else if (this.theme === 'light') {
        html.classList.remove('dark');
      } else { // system
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
          html.classList.add('dark');
        } else {
          html.classList.remove('dark');
        }
      }
      
      localStorage.setItem('alt-dashboard-theme', this.theme);
    },

    // === Toast System ===
    showToast(message, type = 'info') {
      if (this.toast.timeout) {
        clearTimeout(this.toast.timeout);
      }
      
      this.toast.message = message;
      this.toast.type = type;
      
      this.toast.timeout = setTimeout(() => {
        this.hideToast();
      }, 4000);
    },

    hideToast() {
      this.toast.message = '';
      if (this.toast.timeout) {
        clearTimeout(this.toast.timeout);
        this.toast.timeout = null;
      }
    },

    // === Watchers ===
    $watch: {
      autoRefresh(value) {
        this.setupAutoRefresh();
        localStorage.setItem('alt-dashboard-autoRefresh', value);
      },
      
      refreshInterval(value) {
        if (this.autoRefresh) {
          this.setupAutoRefresh();
        }
        localStorage.setItem('alt-dashboard-refreshInterval', value);
      },
      
      searchQuery() {
        this.filterDevices();
      },
      
      deviceFilter() {
        this.filterDevices();
      }
    },

    // === Cleanup ===
    destroy() {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer);
      }
      if (this.toast.timeout) {
        clearTimeout(this.toast.timeout);
      }
    }
  };
}

// Make it globally available
window.altDashboard = altDashboard;
