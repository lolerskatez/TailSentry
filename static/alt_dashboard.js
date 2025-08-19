window.altTailSentry = function altTailSentry() {
  return {
    // Alpine.js state and methods
    darkMode: false,
    openSettings: false,
    peerModal: false,
    selectedPeer: {},
    refreshInterval: 30,
    lastUpdated: '',
    device: {
      hostname: 'Loading...',
      ip: '0.0.0.0',
      role: 'Loading...',
      uptime: '0m',
      isExit: false,
      online: false
    },
    net: { tx: '0.0 MB/s', rx: '0.0 MB/s', activity: 0 },
    peers: [],
    peerFilter: '',
    subnets: [],
    logs: [],
    toast: '',
    authKey: '',
  isExitNode: false,
  isSubnetRouting: false,
  advertisedRoutes: [],
  advertiseIPv4Exit: false,
  advertiseIPv6Exit: false,
  exitNodeFirewall: false, // UI only
  exitNodePeerCount: 0,
  exitNodeLastChanged: '',
  exitNodeLastError: '',
    // Settings UI state
    tailscaleStatus: 'unknown',
    tailscaleIp: '',
    authFeedback: '',
    authSuccess: false,
    // Alpine.js settings page state variables (must be defined for template)
    tailscaleCtlFeedback: '',
    exitNodeFeedback: '',
    subnetModalOpen: false,
    allSubnets: [
      '10.0.0.0/8',
      '172.16.0.0/12',
      '192.168.0.0/16'
    ],
    subnetFeedback: '',

    // Alpine.js methods
    saveHostname() {
      const payload = {
        hostname: this.device.hostname
      };
      this.tailscaleCtlFeedback = '';
      fetch('/api/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.tailscaleCtlFeedback = 'Hostname saved!';
          this.loadStatus();
        } else {
          this.tailscaleCtlFeedback = data.message || 'Failed to save hostname.';
        }
      })
      .catch(() => {
        this.tailscaleCtlFeedback = 'Network or server error.';
      });
    },
    darkMode: false,
    openSettings: false,
    peerModal: false,
    selectedPeer: {},
    refreshInterval: 30,
    lastUpdated: '',
    device: {
      hostname: 'Loading...',
      ip: '0.0.0.0',
      role: 'Loading...',
      uptime: '0m',
      isExit: false,
      online: false
    },
    net: { tx: '0.0 MB/s', rx: '0.0 MB/s', activity: 0 },
    peers: [],
    peerFilter: '',
    subnets: [],
    logs: [],
    toast: '',
    authKey: '',
    isExitNode: false,
    isSubnetRouting: false,
    advertisedRoutes: [],
    // Settings UI state
    tailscaleStatus: 'unknown',
    tailscaleIp: '',
    authFeedback: '',
    authSuccess: false,

    // Alpine.js settings page state variables (must be defined for template)
    tailscaleCtlFeedback: '',
    exitNodeFeedback: '',
    subnetModalOpen: false,
    allSubnets: [
      '10.0.0.0/8',
      '172.16.0.0/12',
      '192.168.0.0/16'
    ],
    subnetFeedback: '',

    // Tailscale Up/Down methods for settings page
    tailscaleUp() {
      const payload = {
        auth_key: this.authKey,
        hostname: this.device.hostname,
        accept_routes: this.device.accept_routes ?? true,
        advertise_exit_node: this.isExitNode,
        advertise_routes: this.advertisedRoutes
      };
      this.tailscaleCtlFeedback = '';
      fetch('/api/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.tailscaleCtlFeedback = 'Tailscale started!';
          this.loadStatus();
        } else {
          this.tailscaleCtlFeedback = data.message || 'Failed to start Tailscale.';
        }
      })
      .catch(() => {
        this.tailscaleCtlFeedback = 'Network or server error.';
      });
    },
    tailscaleDown() {
      this.tailscaleCtlFeedback = '';
      fetch('/api/down', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.tailscaleCtlFeedback = 'Tailscale stopped!';
          this.loadStatus();
        } else {
          this.tailscaleCtlFeedback = data.message || 'Failed to stop Tailscale.';
        }
      })
      .catch(() => {
        this.tailscaleCtlFeedback = 'Network or server error.';
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
      this.darkMode = localStorage.getItem('altDarkMode') === 'true';
      // Optionally load authKey from storage
      const key = localStorage.getItem('tailscale_auth_key');
      if (key) this.authKey = key;
      this.loadAll();
      setInterval(() => this.loadAll(), this.refreshInterval * 1000);
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

    loadAll() {
      this.loadStatus();
      this.loadPeers();
      this.loadSubnets();
      this.loadTraffic();
      this.lastUpdated = new Date().toLocaleTimeString();
    },

    async loadStatus() {
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          const data = await res.json();
          console.log('Status API response:', data);
          // Map fields from data.Self
          const self = data.Self || {};
          this.device.hostname = self.HostName || 'Unknown';
          this.device.ip = (self.TailscaleIPs && self.TailscaleIPs[0]) || '0.0.0.0';
          this.device.role = self.OS || 'Unknown';
          this.device.uptime = this.formatUptime(self.Created || null);
          // Check if AdvertisedRoutes contains 0.0.0.0/0 or ::/0 (exit node)
          const advRoutes = Array.isArray(self.AdvertisedRoutes) ? self.AdvertisedRoutes : [];
          this.advertisedRoutes = advRoutes;
          const isIPv4Exit = advRoutes.includes('0.0.0.0/0');
          const isIPv6Exit = advRoutes.includes('::/0');
          this.advertiseIPv4Exit = isIPv4Exit;
          this.advertiseIPv6Exit = isIPv6Exit;
          const isExitNode = isIPv4Exit || isIPv6Exit;
          this.device.isExit = isExitNode;
          this.device.online = data.BackendState === 'Running';
          this.isExitNode = isExitNode;
          this.device.subnetRoutes = (self.AllowedIPs && self.AllowedIPs.length) || 0;
          // Peers using this as exit node (count peers with ExitNode == this device's ID)
          const myId = self.ID;
          let peerCount = 0;
          if (data.Peer && myId) {
            for (const peerId in data.Peer) {
              const peer = data.Peer[peerId];
              if (peer.ExitNode === myId) peerCount++;
            }
          }
          this.exitNodePeerCount = peerCount;
          // Last changed and last error/log (UI only, could be improved with backend support)
          this.exitNodeLastChanged = localStorage.getItem('exitNodeLastChanged') || '';
          this.exitNodeLastError = localStorage.getItem('exitNodeLastError') || '';
    // Advanced Exit Node apply
    async applyExitNodeAdvanced() {
      // Build advertised routes array
      const routes = [];
      if (this.advertiseIPv4Exit) routes.push('0.0.0.0/0');
      if (this.advertiseIPv6Exit) routes.push('::/0');
      // Add any other advertised routes
      for (const r of this.advertisedRoutes) {
        if (!routes.includes(r) && r !== '0.0.0.0/0' && r !== '::/0') routes.push(r);
      }
      const payload = {
        advertised_routes: routes,
        hostname: this.device.hostname,
        firewall: this.exitNodeFirewall // UI only, backend can ignore or use
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
          const now = new Date().toLocaleString();
          this.exitNodeLastChanged = now;
          localStorage.setItem('exitNodeLastChanged', now);
        } else {
          this.exitNodeFeedback = data.message || 'Failed to apply Exit Node setting.';
          this.exitNodeLastError = this.exitNodeFeedback;
          localStorage.setItem('exitNodeLastError', this.exitNodeFeedback);
        }
      } catch (e) {
        this.exitNodeFeedback = 'Network or server error.';
        this.exitNodeLastError = this.exitNodeFeedback;
        localStorage.setItem('exitNodeLastError', this.exitNodeFeedback);
      }
      this.loadStatus();
    },
          // Extra: user, DNS, version for settings if needed
          this.device.user = (data.User && (data.User.DisplayName || data.User.LoginName)) || '';
          this.device.magicDnsSuffix = data.MagicDNSSuffix || '';
          this.device.version = data.Version || '';

          // Set tailscaleStatus based on backend state and IP
          if (data.BackendState === 'Running' && this.device.ip && this.device.ip !== '0.0.0.0') {
            this.tailscaleStatus = 'authenticated';
            this.tailscaleIp = this.device.ip;
          } else {
            this.tailscaleStatus = 'not_authenticated';
            this.tailscaleIp = '';
          }
        }
      } catch (e) { this.toastMsg('Failed to load status'); }
    },

    async loadPeers() {
      try {
        const res = await fetch('/api/peers');
        if (res.ok) {
          const data = await res.json();
          const peersObj = data.peers || {};
          this.peers = Object.values(peersObj).map(peer => ({
            id: peer.ID || peer.HostName,
            hostname: peer.HostName || 'unknown',
            ip: (peer.TailscaleIPs && peer.TailscaleIPs[0]) || '0.0.0.0',
            os: peer.OS || 'Unknown',
            lastSeen: this.formatLastSeen(peer.LastSeen),
            tags: peer.Tags || [],
            online: peer.Online || false
          }));
        }
      } catch (e) { this.toastMsg('Failed to load peers'); }
    },

    async loadSubnets() {
      try {
        const res = await fetch('/api/subnet-routes');
        if (res.ok) {
          const data = await res.json();
          this.subnets = data.routes || [];
          this.isSubnetRouting = Array.isArray(this.subnets) && this.subnets.length > 0;
          this.advertisedRoutes = this.subnets;
        }
      } catch (e) { this.isSubnetRouting = false; this.advertisedRoutes = []; }
    },

    async loadTraffic() {
      try {
        const res = await fetch('/api/traffic');
        if (res.ok) {
          const data = await res.json();
          this.net.tx = data.traffic?.tx_rate || '0.0 MB/s';
          this.net.rx = data.traffic?.rx_rate || '0.0 MB/s';
          this.net.activity = data.traffic?.activity_level || 0;
        }
      } catch (e) { /* ignore */ }
    },

    refresh() {
      this.loadAll();
      this.toastMsg('Refreshed');
    },

    filteredPeers() {
      if (!this.peerFilter) return this.peers;
      const q = this.peerFilter.toLowerCase();
      return this.peers.filter(p =>
        p.hostname.toLowerCase().includes(q) ||
        p.ip.includes(q) ||
        (p.tags.join(' ').includes(q))
      );
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


    // Settings page Alpine.js methods
    async applyExitNode() {
      // Call backend to apply exit node setting
      const payload = {
        is_exit_node: this.isExitNode,
        hostname: this.device.hostname
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
    toggleSubnet(subnet) {
      if (!this.advertisedRoutes) this.advertisedRoutes = [];
      if (this.advertisedRoutes.includes(subnet)) {
        this.advertisedRoutes = this.advertisedRoutes.filter(s => s !== subnet);
      } else {
        this.advertisedRoutes.push(subnet);
      }
    },
    async applySubnets() {
      // Call backend to apply subnet routes
      const payload = {
        advertised_routes: this.advertisedRoutes,
        hostname: this.device.hostname
      };
      this.subnetFeedback = '';
      try {
        const res = await fetch('/api/authenticate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          this.subnetFeedback = 'Subnet routes applied!';
          this.subnetModalOpen = false;
          this.loadStatus();
        } else {
          this.subnetFeedback = data.message || 'Failed to apply subnet routes.';
        }
      } catch (e) {
        this.subnetFeedback = 'Network or server error.';
      }
    },
    // ...existing code...
    // Advanced Exit Node apply
    async applyExitNodeAdvanced() {
      // Build advertised routes array
      const routes = [];
      if (this.advertiseIPv4Exit) routes.push('0.0.0.0/0');
      if (this.advertiseIPv6Exit) routes.push('::/0');
      // Add any other advertised routes
      for (const r of this.advertisedRoutes) {
        if (!routes.includes(r) && r !== '0.0.0.0/0' && r !== '::/0') routes.push(r);
      }
      const payload = {
        advertised_routes: routes,
        hostname: this.device.hostname,
        firewall: this.exitNodeFirewall // UI only, backend can ignore or use
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
          const now = new Date().toLocaleString();
          this.exitNodeLastChanged = now;
          localStorage.setItem('exitNodeLastChanged', now);
        } else {
          this.exitNodeFeedback = data.message || 'Failed to apply Exit Node setting.';
          this.exitNodeLastError = this.exitNodeFeedback;
          localStorage.setItem('exitNodeLastError', this.exitNodeFeedback);
        }
      } catch (e) {
        this.exitNodeFeedback = 'Network or server error.';
        this.exitNodeLastError = this.exitNodeFeedback;
        localStorage.setItem('exitNodeLastError', this.exitNodeFeedback);
      }
      this.loadStatus();
    },
  // Removed toggleExitNode: always use backend state
    openSubnetModal() { this.toastMsg('Subnet management coming soon!'); },
    openKeyModal() { this.toastMsg('Key management coming soon!'); },
    openLogsModal() { this.toastMsg('Logs coming soon!'); },
    openPeerModal(peer) { this.selectedPeer = peer; this.peerModal = true; },
    pingPeer(peer) { this.toastMsg('Ping to ' + peer.hostname + ' -> 12ms (mock)'); },
    logout() { window.location.href = '/logout'; },
    toastMsg(msg) { this.toast = msg; setTimeout(() => this.toast = '', 3500); },
    $watch: {
      darkMode(val) { localStorage.setItem('altDarkMode', val); },
      refreshInterval(val) { if (val < 5) this.refreshInterval = 5; }
    }
  }
}
window.altTailSentry = altTailSentry;
