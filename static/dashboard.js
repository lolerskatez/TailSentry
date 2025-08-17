/**
 * TailSentry Dashboard JavaScript
 * Handles WebSocket connectivity, real-time updates, and UI interactions
 */

function tailSentry(){
      return {
        dark: false,
        active: 'dashboard',
        lastUpdated: new Date().toLocaleTimeString(),
        device: {
          hostname: 'Loading...',
          ip: '0.0.0.0',
          role: 'Loading...',
          uptime: '0m',
          isExit: false,
          exitDetails: 'Loading...'
        },
        net: { tx: '0.0 MB/s', rx: '0.0 MB/s' },
        peers: [],
        peerFilter: '',
        subnets: [],
        newSubnet: '',
        service: { status: 'unknown', uptime: '0m' },
        logs: [],
        keys: [],
        newKey: { label:'', exp:'7d', reusable:true },
        openAuthKeyModal: false,
        toast: '',
        
        async init(){
          console.log('TailSentry initializing...');
          // restore dark pref
          this.dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
          
          // Load real data immediately
          await this.loadRealData();
          
          // Set up periodic updates every 30 seconds
          setInterval(()=> this.loadRealData(), 30000);
        },

        async loadRealData() {
          try {
            console.log('Loading real Tailscale data...');
            
            // Load device info and status
            const statusResponse = await fetch('/api/status');
            if (statusResponse.ok) {
              const statusData = await statusResponse.json();
              console.log('Status data received:', statusData);
              this.updateDeviceInfo(statusData);
              this.updatePeers(statusData);
            } else {
              console.error('Failed to fetch status:', statusResponse.status);
              this.device.hostname = 'Error loading data';
              this.device.ip = 'Check connection';
            }
            
            // Load subnet routes
            try {
              const subnetResponse = await fetch('/api/subnet-routes');
              if (subnetResponse.ok) {
                const subnetData = await subnetResponse.json();
                this.updateSubnets(subnetData);
              }
            } catch (e) {
              console.warn('Failed to load subnet routes:', e);
            }
            
            this.lastUpdated = new Date().toLocaleTimeString();
            console.log('Real data loaded successfully');
            
          } catch (error) {
            console.error('Error loading real data:', error);
            this.device.hostname = 'Error loading data';
            this.device.ip = 'Check connection';
            this.toastMsg('Failed to load data: ' + error.message);
          }
        },

        updateDeviceInfo(statusData) {
          if (statusData && statusData.Self) {
            this.device.hostname = statusData.Self.HostName || 'unknown';
            this.device.ip = statusData.Self.TailscaleIPs?.[0] || '0.0.0.0';
            this.device.online = statusData.Self.Online || false;
            
            // Update service status
            this.service.status = statusData.BackendState === 'Running' ? 'active' : 'inactive';
            
            // Check if this device is an exit node
            this.device.isExit = statusData.Self.ExitNode || false;
            this.device.exitDetails = this.device.isExit ? 'Advertising exit route' : 'Not advertising exit route';
            
            // Update network stats if available
            if (statusData.Self.TXBytes !== undefined) {
              this.net.tx = this.formatBytes(statusData.Self.TXBytes) + '/s';
            }
            if (statusData.Self.RXBytes !== undefined) {
              this.net.rx = this.formatBytes(statusData.Self.RXBytes) + '/s';
            }
          }
        },

        updatePeers(statusData) {
          // Accepts either the /api/status or /api/peers response
          let peersObj = statusData.Peer || statusData.peers || {};
          this.peers = Object.values(peersObj).map(peer => ({
            id: peer.ID || peer.HostName,
            hostname: peer.HostName || 'unknown',
            ip: (peer.TailscaleIPs && peer.TailscaleIPs[0]) || '0.0.0.0',
            os: peer.OS || 'Unknown',
            lastSeen: this.formatLastSeen(peer.LastSeen),
            tags: peer.Tags || [],
            online: peer.Online || false
          }));
          console.log(`Updated ${this.peers.length} peers from real data`);
        },

        updateSubnets(subnetData) {
          if (subnetData && subnetData.routes) {
            this.subnets = subnetData.routes.map(route => ({
              cidr: route.cidr || route,
              iface: route.interface || 'tailscale0',
              enabled: route.enabled !== false
            }));
          }
        },

        formatLastSeen(lastSeenTime) {
          if (!lastSeenTime) return 'unknown';
          
          const now = new Date();
          const lastSeen = new Date(lastSeenTime);
          const diffMs = now - lastSeen;
          const diffMinutes = Math.floor(diffMs / (1000 * 60));
          
          if (diffMinutes < 1) return 'now';
          if (diffMinutes < 60) return `${diffMinutes}m`;
          
          const diffHours = Math.floor(diffMinutes / 60);
          if (diffHours < 24) return `${diffHours}h`;
          
          const diffDays = Math.floor(diffHours / 24);
          return `${diffDays}d`;
        },

        formatBytes(bytes) {
          if (bytes === 0) return '0 B';
          const k = 1024;
          const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
          const i = Math.floor(Math.log(bytes) / Math.log(k));
          return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },
        refresh(){
          this.lastUpdated = new Date().toLocaleTimeString();
          this.loadRealData();
          this.toastMsg('Refreshed');
        },
        filteredPeers(){
          if(!this.peerFilter) return this.peers;
          const q = this.peerFilter.toLowerCase();
          return this.peers.filter(p => p.hostname.toLowerCase().includes(q) || p.ip.includes(q) || (p.tags.join(' ').includes(q)));
        },
        toggleSubnet(idx){
          let s = this.subnets[idx];
          s.enabled = !s.enabled;
          this.toastMsg((s.enabled ? 'Enabled ' : 'Disabled ') + s.cidr);
        },
        addSubnet(){
          const cidr = this.newSubnet.trim();
          if(!cidr) return this.toastMsg('Enter a CIDR');
          this.subnets.push({cidr, iface:'manual', enabled:true});
          this.newSubnet = '';
          this.toastMsg('Added ' + cidr);
        },
        toggleExitNode(){
          this.device.isExit = !this.device.isExit;
          this.device.exitDetails = this.device.isExit ? 'Advertising as exit node' : 'Not advertising exit route';
          this.toastMsg(this.device.isExit ? 'Exit node enabled (mock)' : 'Exit node disabled (mock)');
        },
        openReauthModal(){
          this.openAuthKeyModal = true;
        },
        serviceAction(action){
          // mock actions
          this.service.status = (action === 'stop' ? 'inactive' : 'active');
          this.toastMsg('Service ' + action + ' (mock)');
          // update logs
          this.logs.unshift(new Date().toLocaleString() + ' - tailscaled: ' + action);
          if(this.logs.length>60) this.logs.pop();
        },
        pingPeer(p){
          this.toastMsg('Ping to ' + p.hostname + ' -> 12ms (mock)');
        },
        openPeerModal(p){
          alert('Peer details (mock)\\n\\n' + JSON.stringify(p, null, 2));
        },
        createKey(){
          const id = 'k' + (this.keys.length+1);
          const label = this.newKey.label || ('key-' + id);
          this.keys.push({id, label, expires: this.newKey.exp, reusable: this.newKey.reusable});
          this.newKey = {label:'',exp:'7d',reusable:true};
          this.toastMsg('Created key ' + label + ' (mock)');
        },
        revokeKey(id){
          this.keys = this.keys.filter(k=>k.id !== id);
          this.toastMsg('Revoked key ' + id + ' (mock)');
        },
        logout(){
          this.toastMsg('Logged out (mock)');
          // in real app redirect to login
        },
        toastMsg(msg){
          this.toast = msg;
          setTimeout(()=> this.toast = '', 3500);
        }
      }
    }
