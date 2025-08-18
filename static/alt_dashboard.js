

window.altTailSentry = function altTailSentry() {
  return {
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
    // Alpine.js global state for settings page
    authKey: '',
    peers: [],
    peerFilter: '',
    subnets: [],
    logs: [],
    toast: '',

    init() {
      this.darkMode = localStorage.getItem('altDarkMode') === 'true';
      this.loadAll();
      setInterval(() => this.loadAll(), this.refreshInterval * 1000);
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
          this.device.hostname = data.Self?.HostName || 'unknown';
          this.device.ip = data.Self?.TailscaleIPs?.[0] || '0.0.0.0';
          this.device.role = data.Self?.Role || 'N/A';
          this.device.uptime = this.formatUptime(data.Self?.Created);
          this.device.isExit = data.Self?.ExitNode || false;
          this.device.online = data.BackendState === 'Running';
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

    toggleExitNode() {
      this.isExitNode = !this.isExitNode;
      this.device.isExit = this.isExitNode;
      this.toastMsg(this.isExitNode ? 'Exit node enabled (mock)' : 'Exit node disabled (mock)');
    },

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
