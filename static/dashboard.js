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
          hostname: 'tailsentry-01',
          ip: '100.64.0.42',
          role: 'Exit Node + Subnet Router',
          uptime: '5d 4h',
          isExit: false,
          exitDetails: 'Not advertising exit route'
        },
        net: { tx: '0.0 MB/s', rx: '0.0 MB/s' },
        peers: [
          { id:1, hostname:'laptop-jane', ip:'100.101.1.12', os:'macOS', lastSeen:'2m', tags:['dev'] },
          { id:2, hostname:'raspi-nas', ip:'100.101.1.20', os:'Linux', lastSeen:'5m', tags:['srv','nas'] },
          { id:3, hostname:'office-ws-01', ip:'100.101.1.32', os:'Windows', lastSeen:'15m', tags:['work'] },
          { id:4, hostname:'phone-andy', ip:'100.101.1.45', os:'Android', lastSeen:'1h', tags:['mobile'] }
        ],
        peerFilter: '',
        subnets: [
          { cidr: '192.168.1.0/24', iface: 'eth0', enabled: true },
          { cidr: '10.0.0.0/24', iface: 'eth1', enabled: false }
        ],
        newSubnet: '',
        service: { status: 'active', uptime: '5d 3h' },
        logs: [
          'Jul 31 10:12:01 tailscaled[123]: starting',
          'Jul 31 10:12:05 tailscaled[123]: authenticated',
          'Jul 31 12:20:11 tailscaled[123]: route added: 192.168.1.0/24'
        ],
        keys: [
          { id: 'k1', label: 'm-pop-7d', expires: '2025-08-01', reusable: false },
          { id: 'k2', label: 'admin-90d', expires: '2025-10-10', reusable: true },
        ],
        newKey: { label:'', exp:'7d', reusable:true },
        openAuthKeyModal: false,
        toast: '',
        init(){
          // restore dark pref
          this.dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
          // fake live update
          setInterval(()=> this.fakeUpdate(), 4000);
        },
        refresh(){
          this.lastUpdated = new Date().toLocaleTimeString();
          this.toastMsg('Refreshed');
        },
        fakeUpdate(){
          // simulate rx/tx updates and last seen
          const rnd = (n)=> (Math.random()*n).toFixed(2);
          this.net.tx = (0.1 + parseFloat(rnd(3))).toFixed(2) + ' MB/s';
          this.net.rx = (0.05 + parseFloat(rnd(2))).toFixed(2) + ' MB/s';
          this.peers.forEach(p => {
            // randomly increment last seen in minutes
            let m = Math.floor(Math.random()*60);
            p.lastSeen = (m < 2 ? 'now' : (m + 'm'));
          });
          this.lastUpdated = new Date().toLocaleTimeString();
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
