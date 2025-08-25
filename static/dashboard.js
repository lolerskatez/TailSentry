// --- Enhanced Alpine.js Dashboard with Robust Error Handling ---
window.dashboard = function dashboard() {
  return {
    // --- Enhanced Settings Export/Import Methods ---
    async exportSettings() {
      this.showLoading('export', true);
      try {
        const response = await fetch('/api/settings/export', { 
          credentials: 'same-origin',
          headers: { 'Accept': 'application/json' }
        });
        
        if (!response.ok) {
          throw new Error(`Export failed: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        const filename = `tailsentry-settings-${new Date().toISOString().slice(0,10)}.json`;
        this.downloadFile(filename, JSON.stringify(data, null, 2));
        this.showToast('Settings exported successfully', 'success');
      } catch (error) {
        console.error('Export error:', error);
        this.showToast('Failed to export settings: ' + error.message, 'error');
      } finally {
        this.showLoading('export', false);
      }
    },
    async importSettings(e) {
      const file = e.target.files[0];
      if (!file) return;
      
      this.showLoading('import', true);
      const reader = new FileReader();
      
      reader.onload = async (evt) => {
        try {
          const settings = JSON.parse(evt.target.result);
          
          const response = await fetch('/api/settings/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(settings)
          });
          
          if (!response.ok) {
            throw new Error(`Import failed: ${response.status} ${response.statusText}`);
          }
          
          await response.json();
          this.showToast('Settings imported successfully', 'success');
          
          // Refresh dashboard data after import
          setTimeout(() => this.loadAll(), 1000);
        } catch (error) {
          console.error('Import error:', error);
          this.showToast('Failed to import settings: ' + error.message, 'error');
        } finally {
          this.showLoading('import', false);
          e.target.value = ''; // Clear file input
        }
      };
      
      reader.onerror = () => {
        this.showToast('Failed to read file', 'error');
        this.showLoading('import', false);
      };
      
      reader.readAsText(file);
    },
    downloadFile(filename, content) {
      try {
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        setTimeout(() => {
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }, 100);
      } catch (error) {
        console.error('Download error:', error);
        this.showToast('Failed to download file', 'error');
      }
    },
    
    showToast(message, type = 'info') {
      this.toast = { message, type, timestamp: Date.now() };
      setTimeout(() => { 
        this.toast = ''; 
      }, type === 'error' ? 5000 : 3000);
      
      // Screen reader accessibility
      const aria = document.getElementById('aria-feedback');
      if (aria) aria.textContent = message;
      
      console.log(`Toast [${type.toUpperCase()}]: ${message}`);
    },
    
    showLoading(operation, isLoading) {
      if (!this.loadingStates) this.loadingStates = {};
      this.loadingStates[operation] = isLoading;
    },
    
    isLoading(operation) {
      return this.loadingStates && this.loadingStates[operation] === true;
    },
    // --- Helper methods for feedback and loading ---
    setFeedback(type, msg) {
      if (type === 'exitNode') {
        this.exitNodeFeedback = msg;
        this.exitNodeLastError = msg;
        localStorage.setItem('exitNodeLastError', msg);
      } else if (type === 'subnet') {
        this.subnetFeedback = msg;
      } else if (type === 'tailscaleCtl') {
        this.tailscaleCtlFeedback = msg;
      }
    },
    setLoading(type, val) {
      if (type === 'exitNode') this.exitNodeLoading = val;
      if (type === 'subnet') this.subnetApplyLoading = val;
    },
    
    // --- Enhanced state variables with better organization ---
    darkMode: false,
    theme: localStorage.getItem('theme') || 'system',
    emailAlerts: false,
    showToasts: true,
    openSettings: false,
    
    // Modal states
    peerModal: false,
    subnetModalOpen: false,
    selectedPeer: {},
    showPeerModal: false,
    
    // Dashboard settings
    refreshInterval: 30,
    lastUpdated: '',
    connectionStatus: 'connecting',
    secureMode: false,
    loadingStates: {},
    autoRefresh: true,
    showCharts: true,
    showQuickSettings: false,
    viewMode: 'detailed',
    isRefreshing: false,
    
    // Alert system
    alertType: null,
    alertMessage: '',
    showAlert: false,
    
    // Search and filtering
    searchFilter: '',
    sortBy: 'hostname',
    
    // Toast system
    toastType: null,
    toastMessage: '',
    
    // Enhanced data structures for new dashboard
    deviceStatus: {
      online: false,
      hostname: 'Loading...',
      ip: '0.0.0.0',
      uptime: '0m',
      isExitNode: false
    },
    
    peersStats: {
      total: 0,
      online: 0,
      offline: 0,
      onlineChange: 0
    },
    
    networkStats: {
      throughput: '0 Mbps',
      upload: '0 KB/s',
      download: '0 KB/s',
      history: []
    },
    
    subnetStats: {
      total: 0,
      advertised: 0,
      accepted: 0
    },
    
    // Device information
    device: {
      hostname: 'Loading...',
      ip: '0.0.0.0',
      role: 'Loading...',
      uptime: '0m',
      isExit: false,
      online: false,
      user: '',
      magicDnsSuffix: '',
      version: '',
      subnetRoutes: 0,
      accept_routes: true
    },
    
    // Network statistics
    net: { 
      tx: '0.0 MB/s', 
      rx: '0.0 MB/s', 
      activity: 0,
      history: []
    },
    peers: [],
    peerFilter: '',
    deviceFilter: 'all', // 'all', 'using-exit', 'online'
    exitNodeClients: [],
    searchFilter: '',
    sortBy: 'hostname',
    viewMode: 'table',
    subnets: [],
    logs: [],
    toast: '',
    manualSubnet: '',
    manualSubnetError: '',
    authKey: '',
    isExitNode: false,
    isSubnetRouting: false,
    advertisedRoutes: [],
    exitNodeFirewall: false, // UI only
    exitNodePeerCount: 0,
    exitNodeLastChanged: '',
    exitNodeLastError: '',
    exitNodeFeedback: '',
    exitNodeLoading: false,
    subnetModalOpen: false,
    allSubnets: [],
    subnetsLoading: false,
    subnetsChanged: false,
    subnetApplyLoading: false,
    subnetFeedback: '',
    // Settings UI state
    tailscaleStatus: 'unknown',
    tailscaleIp: '',
    authFeedback: '',
    authSuccess: false,
    tailscaleCtlFeedback: '',
    // Peer filtering and refresh methods for dashboard
    filteredPeers() {
      let filtered = this.peers;
      
      // Apply search filter
      if (this.searchFilter) {
        const search = this.searchFilter.toLowerCase();
        filtered = filtered.filter(peer =>
          (peer.hostname || '').toLowerCase().includes(search) ||
          (peer.ip || '').toLowerCase().includes(search) ||
          (peer.os || '').toLowerCase().includes(search) ||
          (peer.user || '').toLowerCase().includes(search)
        );
      }
      
      // Apply device type filter
      if (this.deviceFilter === 'using-exit') {
        filtered = filtered.filter(peer => peer.isUsingAsExitNode);
      } else if (this.deviceFilter === 'online') {
        filtered = filtered.filter(peer => peer.online);
      }
      
      // Apply sorting
      filtered.sort((a, b) => {
        switch (this.sortBy) {
          case 'hostname':
            return (a.hostname || '').localeCompare(b.hostname || '');
          case 'status':
            if (a.online !== b.online) return b.online - a.online;
            return (a.hostname || '').localeCompare(b.hostname || '');
          case 'lastSeen':
            return new Date(b.lastSeen || 0) - new Date(a.lastSeen || 0);
          case 'ip':
            return (a.ip || '').localeCompare(b.ip || '');
          default:
            return 0;
        }
      });
      
      return filtered;
    },
    
    onlinePeers() {
      return this.peers.filter(peer => peer.online);
    },
    
    refresh() {
      this.loadAll();
    },
    applyExitNodeAdvanced: async function() {
      // Build advertised routes array
      // Only advertise exit node if enabled
      let routes = [];
      if (this.isExitNode) {
        routes = ['0.0.0.0/0', '::/0'];
      }
      const payload = {
        advertised_routes: routes,
        hostname: this.device.hostname,
        firewall: this.exitNodeFirewall // UI only, backend can ignore or use
      };
      this.exitNodeFeedback = '';
      this.exitNodeLoading = true;
      try {
        const res = await fetch('/api/exit-node', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          this.exitNodeFeedback = 'Exit node setting applied!';
          const now = new Date().toLocaleString();
          this.exitNodeLastChanged = now;
          localStorage.setItem('exitNodeLastChanged', now);
        } else {
          // Show backend error if present
          this.exitNodeFeedback = (data.error || data.message || 'Failed to apply Exit Node setting.');
          this.exitNodeLastError = this.exitNodeFeedback;
          localStorage.setItem('exitNodeLastError', this.exitNodeFeedback);
        }
        // If backend returned status, update UI immediately
        if (data.status && data.status.Self) {
          const self = data.status.Self;
          const advRoutes = Array.isArray(self.AdvertisedRoutes) ? self.AdvertisedRoutes : [];
          this.advertisedRoutes = advRoutes;
          const isExitNode = advRoutes.includes('0.0.0.0/0') || advRoutes.includes('::/0');
          this.device.isExit = isExitNode;
          this.isExitNode = isExitNode;
        }
      } catch (e) {
        this.exitNodeFeedback = (e && e.message) ? e.message : 'Network or server error.';
        this.exitNodeLastError = this.exitNodeFeedback;
        localStorage.setItem('exitNodeLastError', this.exitNodeFeedback);
      } finally {
        this.exitNodeLoading = false;
      }
  // Always refresh the real state from backend after apply
  await this.loadStatus();
  await this.loadSubnets();
    },

    // Tailscale Up/Down methods for settings page
    tailscaleUp() {
      const payload = {
        auth_key: this.authKey,
        hostname: this.device.hostname,
        accept_routes: this.device.accept_routes ?? true,
        advertise_exit_node: this.isExitNode,
        advertise_routes: this.advertisedRoutes
      };
  this.setFeedback('tailscaleCtl', '');
      fetch('/api/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.setFeedback('tailscaleCtl', 'Tailscale started!');
          this.loadStatus();
        } else {
          this.setFeedback('tailscaleCtl', data.message || 'Failed to start Tailscale.');
        }
      })
      .catch(() => {
        this.setFeedback('tailscaleCtl', 'Network or server error.');
      });
    },
    tailscaleDown() {
  this.setFeedback('tailscaleCtl', '');
      fetch('/api/down', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.setFeedback('tailscaleCtl', 'Tailscale stopped!');
          this.loadStatus();
        } else {
          this.setFeedback('tailscaleCtl', data.message || 'Failed to stop Tailscale.');
        }
      })
      .catch(() => {
        this.setFeedback('tailscaleCtl', 'Network or server error.');
      });
    },

    // Save Authentication Key only (no auth attempt)
    saveAuthKey() {
      if (!this.authKey) {
        this.authFeedback = 'Please enter an authentication key.';
        this.authSuccess = false;
        return;
      }
      const payload = { auth_key: this.authKey };
      this.authFeedback = '';
      fetch('/api/save-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.authFeedback = 'Authentication key saved!';
          this.authSuccess = true;
        } else {
          this.authFeedback = data.error || 'Failed to save authentication key.';
          this.authSuccess = false;
        }
      })
      .catch(() => {
        this.authFeedback = 'Network or server error.';
        this.authSuccess = false;
      });
    },

    init() {
      console.log('🚀 Initializing TailSentry Dashboard');
      
      // Load user preferences first
      this.loadPreferences();
      
      // Initialize theme system - unified with appearance settings
      this.theme = localStorage.getItem('theme') || 'system';
      this.applyTheme();
      
      // Watch for system theme changes
      if (this.theme === 'system') {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
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
      
      // Listen for dashboard errors from controller
      window.addEventListener('dashboard-error', (event) => {
        this.showToast(event.detail.error, 'error');
      });
      
      // Initialize connection monitoring
      window.addEventListener('online', () => {
        this.connectionStatus = 'connecting';
        this.showToast('Connection restored', 'success');
        this.loadAll();
      });
      
      window.addEventListener('offline', () => {
        this.connectionStatus = 'offline';
        this.showToast('Connection lost', 'warning');
      });
      
      // Load stored auth key
      const key = localStorage.getItem('tailscale_auth_key');
      if (key) this.authKey = key;
      
      // Initial data load
      this.loadAll();
      
      // Setup refresh interval with error handling
      if (this.autoRefresh) {
        this.setupRefreshInterval();
      }
      
      console.log('✅ Dashboard initialization complete');
    },
    
    setupRefreshInterval() {
      if (this.refreshIntervalId) {
        clearInterval(this.refreshIntervalId);
      }
      
      this.refreshIntervalId = setInterval(() => {
        // Only refresh if page is visible and online
        if (!document.hidden && navigator.onLine && this.connectionStatus !== 'error') {
          this.loadAll();
        }
      }, this.refreshInterval * 1000);
      
      console.log(`⏰ Refresh interval set to ${this.refreshInterval}s`);
    },

    applyTheme() {
      const isDark = this.theme === 'dark' || 
                    (this.theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
      
      this.darkMode = isDark;
      
      if (isDark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      
      // Update dashboard controller theme if available
      if (window.dashboardMethods && window.dashboardMethods.updateTheme) {
        window.dashboardMethods.updateTheme(isDark);
      }
    },

    authenticateTailscale() {
      if (!this.authKey) {
        this.authFeedback = 'Please enter an Auth Key.';
        this.authSuccess = false;
        return;
      }
      // Always send all settings to backend, but only send a valid hostname
      let hostname = this.device.hostname;
      if (!hostname || hostname === 'Loading...') hostname = undefined;
      const payload = {
        auth_key: this.authKey,
        accept_routes: this.device.accept_routes ?? true,
        advertise_exit_node: this.isExitNode,
        advertise_routes: this.advertisedRoutes
      };
      if (hostname) payload.hostname = hostname;
      console.log('Sending to /api/authenticate:', payload);
      fetch('/api/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.authFeedback = 'Tailscale authentication successful!';
          this.authSuccess = true;
          localStorage.setItem('tailscale_auth_key', this.authKey);
          this.tailscaleStatus = 'authenticated';
          // Always update device info after authentication
          this.loadStatus();
        } else {
          this.authFeedback = data.message || 'Authentication failed.';
          this.authSuccess = false;
          this.tailscaleStatus = 'not_authenticated';
        }
      })
      .catch(() => {
        this.authFeedback = 'Network or server error.';
        this.authSuccess = false;
        this.tailscaleStatus = 'not_authenticated';
      });
    },

    // --- Enhanced data loading with error handling ---
    async loadAll() {
      this.connectionStatus = 'loading';
      const startTime = performance.now();
      
      try {
        // Load all data concurrently with individual error handling
        const results = await Promise.allSettled([
          this.loadStatus(),
          this.loadPeers(),
          this.loadSubnets(),
          this.loadExitNodeClients()
        ]);
        
        // After loading both peers and exit node clients, update the peer status
        if (this.peers && this.exitNodeClients) {
          this.updatePeerExitNodeStatus();
        }
        
        // Check for any failures
        const failures = results.filter(result => result.status === 'rejected');
        if (failures.length > 0) {
          console.warn(`${failures.length} API calls failed:`, failures);
        }
        
        // Update connection status
        const successCount = results.filter(result => result.status === 'fulfilled').length;
        if (successCount === 0) {
          this.connectionStatus = 'error';
          this.showToast('Failed to load dashboard data', 'error');
        } else if (successCount < results.length) {
          this.connectionStatus = 'partial';
        } else {
          this.connectionStatus = 'connected';
        }
        
        this.lastUpdated = new Date().toLocaleTimeString();
        
        const loadTime = Math.round(performance.now() - startTime);
        console.log(`Dashboard refresh completed in ${loadTime}ms (${successCount}/${results.length} successful)`);
        
      } catch (error) {
        console.error('Critical error during dashboard refresh:', error);
        this.connectionStatus = 'error';
        this.showToast('Critical dashboard error: ' + error.message, 'error');
      }
    },

    async loadStatus() {
      try {
        const response = await fetch('/api/status', {
          credentials: 'same-origin',
          headers: { 'Accept': 'application/json' }
        });
        
        if (!response.ok) {
          throw new Error(`Status API error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Status API response:', data);
        
        // Check for secure mode (CLI-only)
        this.secureMode = data._tailsentry_secure_mode === 'true';
        if (this.secureMode) {
          console.log('Running in secure mode (CLI-only) - API features disabled');
        }
        
        // Map fields from data.Self with proper validation
        const self = data.Self || {};
        this.device.hostname = self.HostName || 'Unknown';
        this.device.ip = (self.TailscaleIPs && self.TailscaleIPs[0]) || '0.0.0.0';
        this.device.role = self.OS || 'Unknown';
        this.device.uptime = this.formatUptime(self.Created || null);
        
        // Check if AdvertisedRoutes contains 0.0.0.0/0 or ::/0 (exit node)
        const advRoutes = Array.isArray(self.AdvertisedRoutes) ? self.AdvertisedRoutes : [];
        this.advertisedRoutes = advRoutes;
        const isExitNode = advRoutes.includes('0.0.0.0/0') || advRoutes.includes('::/0');
        this.device.isExit = isExitNode;
        this.device.online = data.BackendState === 'Running';
        this.isExitNode = isExitNode;
        this.device.subnetRoutes = (self.AllowedIPs && self.AllowedIPs.length) || 0;
        
        // Count peers using this as exit node
        const myId = self.ID;
        let peerCount = 0;
        if (data.Peer && myId) {
          for (const peerId in data.Peer) {
            const peer = data.Peer[peerId];
            if (peer.ExitNode === myId) peerCount++;
          }
        }
        this.exitNodePeerCount = peerCount;
        
        // Load persistent UI state
        this.exitNodeLastChanged = localStorage.getItem('exitNodeLastChanged') || '';
        this.exitNodeLastError = localStorage.getItem('exitNodeLastError') || '';
        
        // Additional device info
        this.device.user = (data.User && (data.User.DisplayName || data.User.LoginName)) || '';
        this.device.magicDnsSuffix = data.MagicDNSSuffix || '';
        this.device.version = data.Version || '';

        // Set tailscaleStatus based on backend state and IP
        if (data.BackendState === 'Running' && this.device.ip && this.device.ip !== '0.0.0.0') {
          this.tailscaleStatus = 'authenticated';
          this.tailscaleIp = this.device.ip;
        } else if (data.BackendState === 'NeedsLogin' || data.offline_reason === 'tailscale_not_configured') {
          // Tailscale not configured or needs authentication
          this.tailscaleStatus = 'not_authenticated';
          this.tailscaleIp = '';
          // Set offline state for better user experience
          this.device.online = false;
          this.connectionStatus = 'offline';
        } else {
          this.tailscaleStatus = 'not_authenticated';
          this.tailscaleIp = '';
        }
        
        // Update enhanced data structures
        this.updateEnhancedDataStructures();
        
        return data;
      } catch (error) {
        console.error('Failed to load status:', error);
        this.device.online = false;
        this.connectionStatus = 'error';
        throw error; // Re-throw for Promise.allSettled handling
      }
    },

    // Update enhanced data structures for the new dashboard UI
    updateEnhancedDataStructures() {
      // Update deviceStatus
      this.deviceStatus = {
        online: this.device.online,
        hostname: this.device.hostname,
        ip: this.device.ip,
        uptime: this.device.uptime,
        isExitNode: this.device.isExit
      };
      
      // Update peersStats
      const onlinePeers = this.peers.filter(p => p.online).length;
      const offlinePeers = this.peers.length - onlinePeers;
      this.peersStats = {
        total: this.peers.length,
        online: onlinePeers,
        offline: offlinePeers,
        onlineChange: 0 // This would need historical data
      };
      
      // Update networkStats (placeholder values - would need actual network monitoring)
      this.networkStats = {
        throughput: this.net.activity ? `${this.net.activity} Mbps` : '0 Mbps',
        upload: this.net.tx || '0 KB/s',
        download: this.net.rx || '0 KB/s',
        history: this.net.history || []
      };
      
      // Update subnetStats
      this.subnetStats = {
        total: this.subnets.length,
        advertised: this.advertisedRoutes.length,
        accepted: this.device.subnetRoutes || 0
      };
    },

    async loadPeers() {
      try {
        const response = await fetch('/api/peers', {
          credentials: 'same-origin',
          headers: { 'Accept': 'application/json' }
        });
        
        if (!response.ok) {
          throw new Error(`Peers API error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        const peersObj = data.peers || {};
        
        this.peers = Object.values(peersObj).map(peer => ({
          id: peer.ID || peer.HostName || 'unknown',
          hostname: peer.HostName || 'unknown',
          ip: (peer.TailscaleIPs && peer.TailscaleIPs[0]) || '0.0.0.0',
          os: peer.OS || 'Unknown',
          lastSeen: this.formatLastSeen(peer.LastSeen),
          tags: Array.isArray(peer.Tags) ? peer.Tags : [],
          online: Boolean(peer.Online),
          exitNode: peer.ExitNode || null,
          isUsingAsExitNode: false  // Will be updated by exit node clients data
        }));
        
        // Update peer status chart if controller is available
        if (window.dashboardMethods && window.dashboardMethods.updatePeerChart) {
          window.dashboardMethods.updatePeerChart(this.peers);
        }
        
        console.log(`Loaded ${this.peers.length} peers`);
        
        // Update enhanced data structures
        this.updateEnhancedDataStructures();
        
        return this.peers;
      } catch (error) {
        console.error('Failed to load peers:', error);
        this.peers = [];
        throw error;
      }
    },

    async loadSubnets() {
      this.subnetsLoading = true;
      // Load currently advertised routes
      try {
        const res = await fetch('/api/subnet-routes');
        if (res.ok) {
          const data = await res.json();
          this.subnets = data.routes || [];
          this.isSubnetRouting = Array.isArray(this.subnets) && this.subnets.length > 0;
          this.advertisedRoutes = this.subnets;
        }
      } catch (e) { this.isSubnetRouting = false; this.advertisedRoutes = []; }
      // Load all detected local subnets for modal
      try {
        const res = await fetch('/api/local-subnets');
        if (res.ok) {
          const data = await res.json();
          // data.subnets is a list of {cidr, interface, family}
          this.allSubnets = Array.isArray(data.subnets) ? data.subnets : [];
        }
      } catch (e) { this.allSubnets = []; }
      this.subnetsLoading = false;
      this.subnetsChanged = false;
    },
    
    async loadExitNodeClients() {
      try {
        const res = await fetch('/api/exit-node-clients');
        if (res.ok) {
          const data = await res.json();
          this.exitNodeClients = Array.isArray(data.clients) ? data.clients : [];
          
          // Update peer exit node usage information
          this.updatePeerExitNodeStatus();
        } else {
          console.warn('Failed to load exit node clients');
          this.exitNodeClients = [];
        }
      } catch (e) {
        console.error('Error loading exit node clients:', e);
        this.exitNodeClients = [];
      }
    },
    
    updatePeerExitNodeStatus() {
      // Mark peers that are using this device as exit node
      if (this.peers && this.exitNodeClients.length > 0) {
        this.peers.forEach(peer => {
          peer.isUsingAsExitNode = this.exitNodeClients.some(
            client => client.id === peer.id || client.hostname === peer.hostname
          );
        });
      }
    },
    
    toggleSubnet(subnet) {
      if (!this.advertisedRoutes) this.advertisedRoutes = [];
      if (this.advertisedRoutes.includes(subnet)) {
        this.advertisedRoutes = this.advertisedRoutes.filter(s => s !== subnet);
      } else {
        this.advertisedRoutes = [...this.advertisedRoutes, subnet];
      }
      this.subnetsChanged = true;
    },
    toggleSelectAllSubnets(e) {
      if (e.target.checked) {
        this.advertisedRoutes = this.allSubnets.map(s => s.cidr);
      } else {
        this.advertisedRoutes = [];
      }
      this.subnetsChanged = true;
    },

    formatUptime(created) {
      if (!created) return '0m';
      const then = new Date(created);
      const now = new Date();
      const diff = Math.floor((now - then) / 1000);
      if (diff < 60) return `${diff}s`;
      if (diff < 3600) return `${Math.floor(diff/60)}m`;
      if (diff < 86400) return `${Math.floor(diff/3600)}h`;
      return `${Math.floor(diff/86400)}d`;
    },

    formatLastSeen(lastSeen) {
      if (!lastSeen || lastSeen.startsWith('0001')) return 'unknown';
      const then = new Date(lastSeen);
      const now = new Date();
      const diff = Math.floor((now - then) / 1000);
      if (diff < 60) return `${diff}s ago`;
      if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
      return `${Math.floor(diff/86400)}d ago`;
    },

    showPeerDetails(peer) {
      // Log for debugging
      console.log('showPeerDetails called with:', peer);
      
      // Only show modal if a valid peer is provided
      if (!peer || (!peer.id && !peer.hostname)) {
        console.warn('showPeerDetails called without valid peer data:', peer);
        return;
      }
      
      try {
        // Create a clean copy of the peer data to avoid reactivity issues
        const peerCopy = JSON.parse(JSON.stringify(peer));
        console.log('Setting selectedPeer with clean copy:', peerCopy);
        
        // First set the peer data, then show the modal
        this.selectedPeer = peerCopy;
        
        // Force a manual DOM update before showing the modal
        setTimeout(() => {
          this.showPeerModal = true;
          console.log('Modal should be visible now. showPeerModal =', this.showPeerModal);
          
          // Extra safety check - if modal still not visible, try once more
          setTimeout(() => {
            if (!document.querySelector('[x-show\\.transition\\.opacity="showPeerModal"]')?.offsetHeight) {
              console.log('Modal still not visible, forcing visibility');
              document.querySelector('[x-show\\.transition\\.opacity="showPeerModal"]').style.display = 'flex';
            }
          }, 100);
        }, 50);
      } catch (error) {
        console.error('Error showing peer modal:', error);
      }
    },

    closePeerModal() {
      console.log('Closing peer modal');
      this.showPeerModal = false;
      
      // Clean up after animation completes
      setTimeout(() => {
        this.selectedPeer = {};
        console.log('Modal closed and peer data cleared');
      }, 300);
    },

    sortPeers() {
      // This function is called when the sort dropdown changes
      // Alpine.js will automatically re-compute filteredPeers() when sortBy changes
      // No additional action needed since filtering/sorting is handled in filteredPeers()
    },

    filterPeers() {
      // This function is called when filter dropdown changes
      // Alpine.js will automatically re-compute filteredPeers() when filter changes
      // No additional action needed since filtering is handled in filteredPeers()
    },

    dismissAlert() {
      // Dismiss dashboard alerts
      this.showAlert = false;
    },


    // Settings page Alpine.js methods
    async applyExitNode() {
      // Call backend to apply exit node setting
      const payload = {
  routes: this.advertisedRoutes,
  hostname: this.device.hostname,
      };
      this.exitNodeFeedback = '';
      try {
        const res = await fetch('/api/exit-node', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          this.exitNodeFeedback = 'Exit node setting applied!';
        } else {
          this.exitNodeFeedback = data.message || 'Failed to apply Exit Node setting.';
        }
      } catch (e) {
        this.exitNodeFeedback = 'Network or server error.';
      }
      // Always refresh the real state from backend after apply
      this.loadStatus();
    },

    toggleSelectAllSubnets(e) {
      if (e.target.checked) {
        this.advertisedRoutes = this.allSubnets.map(s => s.cidr);
      } else {
        this.advertisedRoutes = [];
      }
      this.subnetsChanged = true;
    },
    openSubnetModal() {
      this.loadSubnets();
      this.subnetModalOpen = true;
  this.manualSubnet = '';
  this.manualSubnetError = '';
    },
    addManualSubnet() {
      // Validate subnet format (basic CIDR check)
      const cidr = this.manualSubnet.trim();
      const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
      if (!cidrRegex.test(cidr)) {
        this.manualSubnetError = 'Invalid CIDR format (e.g. 192.168.1.0/24)';
        return;
      }
      // Check for duplicate
      if (this.allSubnets.some(s => s.cidr === cidr)) {
        this.manualSubnetError = 'Subnet already in list.';
        return;
      }
      // Add to allSubnets
      this.allSubnets.push({ cidr, interface: 'manual', family: 'IPv4' });
      this.manualSubnet = '';
      this.manualSubnetError = '';
      this.subnetsChanged = true;
    },
    async applySubnets() {
      // Use helpers for feedback and loading state
      const payload = {
        routes: this.advertisedRoutes
      };
      this.setFeedback('subnet', '');
      this.setLoading('subnet', true);
      try {
        const res = await fetch('/api/subnet-routes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          this.setFeedback('subnet', 'Subnet routes applied!');
          this.toastMsg('Subnet routes applied!');
          this.subnetModalOpen = false;
          // Always reload subnets and status to reflect new state
          await this.loadSubnets();
          await this.loadStatus();
        } else {
          this.setFeedback('subnet', data.error || data.message || 'Failed to apply subnet routes.');
        }
      } catch (e) {
        this.setFeedback('subnet', (e && e.message) ? e.message : 'Network or server error.');
      } finally {
        this.setLoading('subnet', false);
      }
    },
    // ...existing code...
    // Advanced Exit Node apply
    async applyExitNodeAdvanced() {
      // Use helpers for feedback and loading state
      const routes = [];
      // Build routes based on isExitNode and advertisedRoutes
      if (this.isExitNode) {
        routes.push('0.0.0.0/0', '::/0');
      }
      for (const r of this.advertisedRoutes) {
        if (!routes.includes(r) && r !== '0.0.0.0/0' && r !== '::/0') routes.push(r);
      }
      const payload = {
        advertise_routes: routes,
        hostname: this.device.hostname,
        exit_node_firewall: this.exitNodeFirewall
      };
      this.setFeedback('exitNode', '');
      this.setLoading('exitNode', true);
      try {
        const res = await fetch('/api/exit-node', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          this.setFeedback('exitNode', 'Exit node setting applied!');
          const now = new Date().toLocaleString();
          this.exitNodeLastChanged = now;
          localStorage.setItem('exitNodeLastChanged', now);
        } else {
          this.setFeedback('exitNode', data.message || 'Failed to apply Exit Node setting.');
        }
      } catch (e) {
        this.setFeedback('exitNode', 'Network or server error.');
      } finally {
        this.setLoading('exitNode', false);
      }
      this.loadStatus();
    },
  // Removed toggleExitNode: always use backend state
    toggleExitNode() {
      this.isExitNode = !this.isExitNode;
      this.applyExitNodeAdvanced();
    },
    regenerateAuthKey() {
      this.toastMsg('Auth key regeneration coming soon!');
    },
    openKeyModal() { this.toastMsg('Key management coming soon!'); },
    openLogsModal() { this.toastMsg('Logs coming soon!'); },
    openPeerModal(peer) { this.selectedPeer = peer; this.peerModal = true; },
    pingPeer(peer) { this.toastMsg('Ping to ' + peer.hostname + ' -> 12ms (mock)'); },
    logout() { window.location.href = '/logout'; },
    toastMsg(msg) { this.toast = msg; setTimeout(() => this.toast = '', 3500); },
    
    // --- Additional methods for enhanced dashboard ---
    refreshAll() {
      this.isRefreshing = true;
      this.loadAll().finally(() => {
        this.isRefreshing = false;
      });
    },
    
    toggleAutoRefresh() {
      this.autoRefresh = !this.autoRefresh;
      if (this.autoRefresh) {
        this.setupRefreshInterval();
      } else {
        if (this.refreshIntervalId) {
          clearInterval(this.refreshIntervalId);
          this.refreshIntervalId = null;
        }
      }
      this.savePreferences();
    },
    
    updateRefreshInterval() {
      if (this.refreshInterval < 5) this.refreshInterval = 5;
      if (this.autoRefresh) {
        this.setupRefreshInterval();
      }
      this.savePreferences();
    },
    
    toggleCharts() {
      this.showCharts = !this.showCharts;
      this.savePreferences();
      
      // Restart dashboard controller charts when shown
      if (this.showCharts && window.dashboardMethods) {
        setTimeout(() => {
          window.dashboardMethods.restart();
        }, 100);
      }
    },
    
    savePreferences() {
      const prefs = {
        autoRefresh: this.autoRefresh,
        showCharts: this.showCharts,
        viewMode: this.viewMode,
        refreshInterval: this.refreshInterval
      };
      localStorage.setItem('dashboard_preferences', JSON.stringify(prefs));
    },
    
    loadPreferences() {
      try {
        const prefs = localStorage.getItem('dashboard_preferences');
        if (prefs) {
          const parsed = JSON.parse(prefs);
          this.autoRefresh = parsed.autoRefresh !== false;
          this.showCharts = parsed.showCharts !== false;
          this.viewMode = parsed.viewMode || 'detailed';
          this.refreshInterval = parsed.refreshInterval || 30;
        }
      } catch (error) {
        console.warn('Failed to load dashboard preferences:', error);
      }
    },
    
    $watch: {
      theme(val) { 
        localStorage.setItem('theme', val); 
        this.applyTheme();
      },
      refreshInterval(val) { 
        if (val < 5) this.refreshInterval = 5;
        if (this.autoRefresh) this.updateRefreshInterval();
      }
    }
  }
}
