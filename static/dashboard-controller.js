// TailSentry Dashboard Controller - Enhanced Robust Implementation
// Provides centralized dashboard state management, real-time monitoring, and chart integration

class DashboardController {
  constructor() {
    this.charts = {};
    this.intervals = {};
    this.isVisible = true;
    this.lastNetworkData = [];
    this.maxDataPoints = 20;
    this.retryCount = 0;
    this.maxRetries = 3;
    
    // Bind methods to preserve context
    this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
    this.initializeCharts = this.initializeCharts.bind(this);
    this.updateNetworkChart = this.updateNetworkChart.bind(this);
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }

  init() {
    console.log('🚀 Initializing TailSentry Dashboard Controller');
    
    // Setup visibility API for performance optimization
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    
    // Initialize charts after a brief delay to ensure DOM elements exist
    setTimeout(() => {
      this.initializeCharts();
      this.startNetworkMonitoring();
    }, 500);

    // Setup error recovery
    window.addEventListener('error', (event) => {
      console.error('Dashboard error:', event.error);
      this.handleError('Dashboard runtime error', event.error);
    });

    // Setup connection monitoring
    window.addEventListener('online', () => {
      console.log('🌐 Connection restored');
      this.retryCount = 0;
      this.restartMonitoring();
    });

    window.addEventListener('offline', () => {
      console.log('📡 Connection lost');
      this.stopMonitoring();
    });
  }

  handleVisibilityChange() {
    this.isVisible = !document.hidden;
    
    if (this.isVisible) {
      console.log('👁️ Dashboard visible - resuming monitoring');
      this.restartMonitoring();
    } else {
      console.log('🙈 Dashboard hidden - pausing monitoring');
      this.pauseMonitoring();
    }
  }

  initializeCharts() {
    try {
      this.initNetworkChart();
      this.initPeerStatusChart();
      console.log('📊 Charts initialized successfully');
    } catch (error) {
      console.error('❌ Chart initialization failed:', error);
      this.handleError('Chart initialization failed', error);
    }
  }

  initNetworkChart() {
    const ctx = document.getElementById('networkChart');
    if (!ctx) {
      console.warn('⚠️ Network chart canvas not found');
      return;
    }

    this.charts.network = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Upload (MB/s)',
            data: [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4
          },
          {
            label: 'Download (MB/s)',
            data: [],
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: {
              usePointStyle: true,
              color: document.documentElement.classList.contains('dark') ? '#f3f4f6' : '#374151'
            }
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(17, 24, 39, 0.9)',
            titleColor: '#f3f4f6',
            bodyColor: '#f3f4f6',
            borderColor: '#374151',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: 'Time',
              color: document.documentElement.classList.contains('dark') ? '#f3f4f6' : '#374151'
            },
            grid: {
              color: document.documentElement.classList.contains('dark') ? '#374151' : '#e5e7eb'
            },
            ticks: {
              color: document.documentElement.classList.contains('dark') ? '#f3f4f6' : '#374151'
            }
          },
          y: {
            display: true,
            title: {
              display: true,
              text: 'Speed (MB/s)',
              color: document.documentElement.classList.contains('dark') ? '#f3f4f6' : '#374151'
            },
            grid: {
              color: document.documentElement.classList.contains('dark') ? '#374151' : '#e5e7eb'
            },
            ticks: {
              color: document.documentElement.classList.contains('dark') ? '#f3f4f6' : '#374151'
            },
            beginAtZero: true
          }
        },
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false
        },
        animation: {
          duration: 0 // Disable animation for real-time updates
        }
      }
    });
  }

  initPeerStatusChart() {
    const ctx = document.getElementById('peerChart');
    if (!ctx) {
      console.warn('⚠️ Peer status chart canvas not found');
      return;
    }

    this.charts.peerStatus = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Online', 'Offline', 'Unknown'],
        datasets: [{
          data: [0, 0, 0],
          backgroundColor: [
            '#10b981', // green for online
            '#ef4444', // red for offline  
            '#6b7280'  // gray for unknown
          ],
          borderWidth: 2,
          borderColor: document.documentElement.classList.contains('dark') ? '#1f2937' : '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              usePointStyle: true,
              color: document.documentElement.classList.contains('dark') ? '#f3f4f6' : '#374151',
              padding: 20
            }
          },
          tooltip: {
            backgroundColor: 'rgba(17, 24, 39, 0.9)',
            titleColor: '#f3f4f6',
            bodyColor: '#f3f4f6',
            borderColor: '#374151',
            borderWidth: 1
          }
        }
      }
    });
  }

  async startNetworkMonitoring() {
    if (this.intervals.network) {
      clearInterval(this.intervals.network);
    }

    // Initial load
    await this.updateNetworkData();

    // Start interval monitoring
    this.intervals.network = setInterval(async () => {
      if (this.isVisible && navigator.onLine) {
        await this.updateNetworkData();
      }
    }, 5000); // Update every 5 seconds

    console.log('📈 Network monitoring started');
  }

  async updateNetworkData() {
    try {
      const response = await fetch('/api/network-stats', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success) {
        this.updateNetworkChart(data.stats);
        this.retryCount = 0; // Reset retry count on success
      } else {
        throw new Error(data.error || 'Network stats request failed');
      }
    } catch (error) {
      console.error('❌ Failed to fetch network stats:', error);
      this.handleNetworkError(error);
    }
  }

  updateNetworkChart(stats) {
    if (!this.charts.network || !stats) return;

    const now = new Date();
    const timeLabel = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    // Parse network speeds (convert from bytes to MB)
    const uploadMB = this.parseNetworkSpeed(stats.tx) / (1024 * 1024);
    const downloadMB = this.parseNetworkSpeed(stats.rx) / (1024 * 1024);

    // Add new data point
    this.charts.network.data.labels.push(timeLabel);
    this.charts.network.data.datasets[0].data.push(uploadMB);
    this.charts.network.data.datasets[1].data.push(downloadMB);

    // Keep only the last maxDataPoints
    if (this.charts.network.data.labels.length > this.maxDataPoints) {
      this.charts.network.data.labels.shift();
      this.charts.network.data.datasets[0].data.shift();
      this.charts.network.data.datasets[1].data.shift();
    }

    this.charts.network.update('none'); // Update without animation
  }

  parseNetworkSpeed(speedStr) {
    if (!speedStr || typeof speedStr !== 'string') return 0;
    
    const match = speedStr.match(/([0-9.]+)\s*([KMGT]?B)/i);
    if (!match) return 0;
    
    const value = parseFloat(match[1]);
    const unit = match[2].toUpperCase();
    
    const multipliers = {
      'B': 1,
      'KB': 1024,
      'MB': 1024 * 1024,
      'GB': 1024 * 1024 * 1024,
      'TB': 1024 * 1024 * 1024 * 1024
    };
    
    return value * (multipliers[unit] || 1);
  }

  updatePeerStatusChart(peers) {
    if (!this.charts.peerStatus || !Array.isArray(peers)) return;

    const statusCounts = peers.reduce((counts, peer) => {
      if (peer.online === true) {
        counts.online++;
      } else if (peer.online === false) {
        counts.offline++;
      } else {
        counts.unknown++;
      }
      return counts;
    }, { online: 0, offline: 0, unknown: 0 });

    this.charts.peerStatus.data.datasets[0].data = [
      statusCounts.online,
      statusCounts.offline,
      statusCounts.unknown
    ];

    this.charts.peerStatus.update();
  }

  handleNetworkError(error) {
    this.retryCount++;
    
    if (this.retryCount <= this.maxRetries) {
      console.log(`🔄 Retrying network request (${this.retryCount}/${this.maxRetries})`);
      setTimeout(() => {
        this.updateNetworkData();
      }, Math.pow(2, this.retryCount) * 1000); // Exponential backoff
    } else {
      console.error('💥 Max retries exceeded for network monitoring');
      this.handleError('Network monitoring failed', error);
    }
  }

  handleError(context, error) {
    const errorMessage = `${context}: ${error.message || error}`;
    console.error('🚨 Dashboard Error:', errorMessage);
    
    // Could emit custom event for dashboard to show error toast
    window.dispatchEvent(new CustomEvent('dashboard-error', {
      detail: { context, error: errorMessage }
    }));
  }

  updateTheme(isDark) {
    // Update chart colors based on theme
    Object.values(this.charts).forEach(chart => {
      if (chart && chart.options) {
        const textColor = isDark ? '#f3f4f6' : '#374151';
        const gridColor = isDark ? '#374151' : '#e5e7eb';
        
        // Update scale colors
        if (chart.options.scales) {
          Object.values(chart.options.scales).forEach(scale => {
            if (scale.title) scale.title.color = textColor;
            if (scale.ticks) scale.ticks.color = textColor;
            if (scale.grid) scale.grid.color = gridColor;
          });
        }
        
        // Update legend colors
        if (chart.options.plugins && chart.options.plugins.legend) {
          chart.options.plugins.legend.labels.color = textColor;
        }
        
        chart.update();
      }
    });
  }

  restartMonitoring() {
    if (!this.isVisible || !navigator.onLine) return;
    
    this.stopMonitoring();
    this.startNetworkMonitoring();
  }

  pauseMonitoring() {
    // Keep intervals but skip updates when not visible
    console.log('⏸️ Monitoring paused');
  }

  stopMonitoring() {
    Object.values(this.intervals).forEach(interval => {
      if (interval) clearInterval(interval);
    });
    this.intervals = {};
    console.log('⏹️ Monitoring stopped');
  }

  destroy() {
    this.stopMonitoring();
    
    // Destroy charts
    Object.values(this.charts).forEach(chart => {
      if (chart && typeof chart.destroy === 'function') {
        chart.destroy();
      }
    });
    this.charts = {};
    
    // Remove event listeners
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    
    console.log('🧹 Dashboard controller destroyed');
  }
}

// Global dashboard controller instance
window.dashboardController = new DashboardController();

// Expose methods for Alpine.js integration
window.dashboardMethods = {
  updatePeerChart: (peers) => window.dashboardController.updatePeerStatusChart(peers),
  updateTheme: (isDark) => window.dashboardController.updateTheme(isDark),
  restart: () => window.dashboardController.restartMonitoring(),
  stop: () => window.dashboardController.stopMonitoring()
};
