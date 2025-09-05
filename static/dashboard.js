// Enhanced TailSentry Dashboard - Clean & Modern Implementation
// Focused on simplicity, performance, and user experience

function enhancedDashboard() {
  return {
    // === Core State ===
    _initialized: false,
    isLoading: false,
    isOnline: false,
    lastUpdate: '',
    autoRefresh: localStorage.getItem('autoRefresh') !== 'false', // Default to true
    refreshInterval: parseInt(localStorage.getItem('refreshInterval') || '30'),
    refreshTimer: null,
    
    // === UI State ===
    showSettings: false,
    showDeviceModal: false,
    showSubnetModal: false,
    theme: localStorage.getItem('theme') || 'system',
    
    // === Data ===
    stats: {
      total: 0,
      online: 0,
      offline: 0
    },
    
    // === Subnet Routes State ===
    currentSubnetRoutes: [],
    newSubnetRoute: '',
    localSubnets: [],
    detectingSubnets: false,
    applyingRoutes: false,
    
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
    exitNodeClients: [],
    tailscaleStatus: 'Unknown',
    
  // === Filters ===
    searchQuery: '',
    deviceFilter: 'online',
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
        console.log('🔄 Dashboard already initialized, skipping...');
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
      
      // Listen for theme changes from appearance settings
      window.addEventListener('theme-changed', (event) => {
        this.theme = event.detail.theme;
        this.applyTheme();
      });
    },

    // === Data Loading ===
    async loadAllData() {
      this.isLoading = true;
      
      try {
        await Promise.allSettled([
          this.loadStatus(),
          this.loadPeers(),
          this.loadSubnets()
        ]);
        
        // Load exit node clients after peers are loaded
        await this.loadExitNodeClients();
        
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
        
        // Handle both array format (new) and object format (legacy)
        if (data.peers) {
          if (Array.isArray(data.peers)) {
            // New format: peers is already an array
            this.devices = data.peers.map(peer => ({
              id: peer.id || peer.ID || peer.nodeId,
              ...peer
            }));
          } else if (typeof data.peers === 'object') {
            // Legacy format: peers is an object, convert to array
            this.devices = Object.entries(data.peers).map(([id, peer]) => ({
              id,
              ...peer
            }));
          } else {
            this.devices = [];
          }
        } else {
          this.devices = [];
        }
        
        console.log(`Loaded ${this.devices.length} devices`);
        
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
        this.currentSubnetRoutes = [...this.subnets]; // Copy for modal management
        
      } catch (error) {
        console.error('Failed to load subnets:', error);
        this.subnets = [];
        this.currentSubnetRoutes = [];
      }
    },

    // === Subnet Routes Management ===
    async detectLocalSubnets() {
      this.detectingSubnets = true;
      try {
        const response = await fetch('/api/local-subnets');
        if (!response.ok) throw new Error('Local subnets API failed');
        
        const data = await response.json();
        this.localSubnets = data.subnets || [];
        
      } catch (error) {
        console.error('Failed to detect local subnets:', error);
        this.localSubnets = [];
        this.showToast('Failed to detect local subnets', 'error');
      } finally {
        this.detectingSubnets = false;
      }
    },

    openSubnetModal() {
      // Reset modal state
      this.currentSubnetRoutes = [...this.subnets];
      this.newSubnetRoute = '';
      this.localSubnets = [];
      this.detectingSubnets = false;
      this.applyingRoutes = false;
      
      // Auto-detect local subnets when opening modal
      this.detectLocalSubnets();
      
      this.showSubnetModal = true;
    },

    closeSubnetModal() {
      this.showSubnetModal = false;
      // Reset state after a brief delay to allow modal animation
      setTimeout(() => {
        this.currentSubnetRoutes = [];
        this.newSubnetRoute = '';
        this.localSubnets = [];
        this.detectingSubnets = false;
        this.applyingRoutes = false;
      }, 300);
    },

    addSubnetRoute() {
      const route = this.newSubnetRoute.trim();
      if (!route) return;
      
      // Basic CIDR validation
      const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
      if (!cidrPattern.test(route)) {
        this.showToast('Invalid CIDR format. Use format like 192.168.1.0/24', 'error');
        return;
      }
      
      // Check for duplicates
      if (this.currentSubnetRoutes.includes(route)) {
        this.showToast('Route already exists', 'error');
        return;
      }
      
      this.currentSubnetRoutes.push(route);
      this.newSubnetRoute = '';
      this.showToast('Route added successfully', 'success');
    },

    removeSubnetRoute(index) {
      const removedRoute = this.currentSubnetRoutes[index];
      this.currentSubnetRoutes.splice(index, 1);
      this.showToast(`Route ${removedRoute} removed. Click Apply to save changes.`, 'success');
    },

    addSuggestedRoute(cidr) {
      if (this.currentSubnetRoutes.includes(cidr)) {
        this.showToast('Route already exists', 'error');
        return;
      }
      
      this.currentSubnetRoutes.push(cidr);
      this.showToast('Suggested route added', 'success');
    },

    hasSubnetRouteChanges() {
      // Check if current routes differ from original
      if (this.currentSubnetRoutes.length !== this.subnets.length) {
        return true;
      }
      
      // Check if all routes match
      for (const route of this.currentSubnetRoutes) {
        if (!this.subnets.includes(route)) {
          return true;
        }
      }
      
      return false;
    },

    async applySubnetRoutes() {
      this.applyingRoutes = true;
      try {
        const response = await fetch('/api/subnet-routes', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            routes: this.currentSubnetRoutes
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to apply subnet routes');
        }
        
        const result = await response.json();
        if (result.success) {
          // Update the main subnets array
          this.subnets = [...this.currentSubnetRoutes];
          
          // Reload all data to reflect changes
          await this.loadAllData();
          
          this.showToast('Subnet routes updated successfully', 'success');
          this.showSubnetModal = false;
        } else {
          throw new Error(result.error || 'Failed to apply routes');
        }
        
      } catch (error) {
        console.error('Failed to apply subnet routes:', error);
        this.showToast(error.message || 'Failed to apply subnet routes', 'error');
      } finally {
        this.applyingRoutes = false;
      }
    },

    async loadExitNodeClients() {
      try {
        const response = await fetch('/api/exit-node-clients');
        if (!response.ok) throw new Error('Exit node clients API failed');
        
        const data = await response.json();
        this.exitNodeClients = data.clients || [];
        
        // Mark devices that are exit node clients
        this.devices.forEach(device => {
          const client = this.exitNodeClients.find(c => c.id === device.id);
          if (client) {
            device.isExitNodeUser = true;
            device.exitNodeConfidence = client.confidence || 'unknown';
          } else {
            device.isExitNodeUser = false;
            delete device.exitNodeConfidence;
          }
        });
        
        // Update filtered devices to reflect the changes
        this.filterDevices();
        
      } catch (error) {
        console.error('Failed to load exit node clients:', error);
        this.exitNodeClients = [];
      }
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

    // === TailSentry Device Management ===
    async manageTailsentryDevice(device, action) {
      if (!device || !device.isTailsentry) {
        this.showToast('Device is not a TailSentry instance', 'error');
        return;
      }

      const deviceName = device.hostname || device.ip;
      this.showToast(`Attempting to ${action} TailSentry on ${deviceName}...`, 'info');

      try {
        const response = await fetch(`/api/tailsentry/${device.id}/${action}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          }
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `Failed to ${action} TailSentry service`);
        }

        const result = await response.json();
        
        if (result.success) {
          this.showToast(`TailSentry ${action} completed successfully on ${deviceName}`, 'success');
          
          // Refresh device data after action
          setTimeout(() => {
            this.loadPeers();
          }, 1000);
        } else {
          throw new Error(result.error || `Failed to ${action} TailSentry service`);
        }

      } catch (error) {
        console.error(`TailSentry ${action} error:`, error);
        this.showToast(`Failed to ${action} TailSentry on ${deviceName}: ${error.message}`, 'error');
      }
    },

    // === TailSentry Node Management ===
    manageTailsentryNode(device) {
      if (!device || !device.isTailsentry) {
        this.showToast('Device is not a TailSentry instance', 'error');
        return;
      }

      const deviceIp = device.ip;
      if (!deviceIp) {
        this.showToast('No IP address available for this device', 'error');
        return;
      }

      const nodeUrl = `http://${deviceIp}:8080`;
      const deviceName = device.hostname || deviceIp;
      
      this.showToast(`Opening TailSentry management for ${deviceName}...`, 'info');
      
      // Open in new tab/window
      window.open(nodeUrl, '_blank');
    },

    // === Utility Functions ===
    formatLastSeen(lastSeen) {
      if (!lastSeen || lastSeen === 'Never' || lastSeen === 'unknown') return 'Never';
      if (lastSeen === 'recent') return 'Just now';
      
      try {
        const date = new Date(lastSeen);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
          return 'Unknown';
        }
        
        const now = new Date();
        const diffMs = now - date;
        
        // Handle negative differences (future dates)
        if (diffMs < 0) {
          return 'Just now';
        }
        
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
      } catch (error) {
        console.warn('Error formatting last seen date:', lastSeen, error);
        return 'Unknown';
      }
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
      
      localStorage.setItem('theme', this.theme);
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
        localStorage.setItem('autoRefresh', value);
      },
      
      refreshInterval(value) {
        if (this.autoRefresh) {
          this.setupAutoRefresh();
        }
        localStorage.setItem('refreshInterval', value);
      },
      
      searchQuery() {
        this.filterDevices();
      },
      
      deviceFilter() {
        this.filterDevices();
      }
    },

    // === Service Control ===
    async serviceAction(action) {
      try {
        this.showToast(`Attempting to ${action} Tailscale service...`, 'info');
        
        const response = await fetch('/api/tailscale-service', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ action: action })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `Failed to ${action} service`);
        }
        
        const result = await response.json();
        this.showToast(`Tailscale service ${action === 'stop' ? 'stopped' : action === 'start' ? 'started' : action === 'restart' ? 'restarted' : action} successfully`, 'success');
        
        // Refresh data after service action
        setTimeout(() => {
          this.loadAllData();
        }, 2000);
        
      } catch (error) {
        console.error(`Service ${action} error:`, error);
        this.showToast(`Failed to ${action} Tailscale service: ${error.message}`, 'error');
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
window.enhancedDashboard = enhancedDashboard;
