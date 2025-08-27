console.log('Testing dashboard.js...');
const fs = require('fs');
const content = fs.readFileSync('static/dashboard.js', 'utf8');

// Create a minimal window-like object
global.window = {
  localStorage: {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {}
  },
  location: { pathname: '/dashboard' },
  console: console
};

// Execute the dashboard.js content
eval(content);

// Test if window.dashboard exists
console.log('window.dashboard exists:', typeof window.dashboard);
console.log('window.enhancedDashboard exists:', typeof window.enhancedDashboard);

if (typeof window.dashboard === 'function') {
  const instance = window.dashboard();
  console.log('Dashboard instance created');
  console.log('Has subnetStats:', 'subnetStats' in instance);
  console.log('Has tailscaleStatus:', 'tailscaleStatus' in instance);
  console.log('Has peers:', 'peers' in instance);
  console.log('Has deviceFilter:', 'deviceFilter' in instance);
  console.log('Has viewMode:', 'viewMode' in instance);
  console.log('Has searchFilter:', 'searchFilter' in instance);
  console.log('Has sortBy:', 'sortBy' in instance);
  console.log('Has init method:', typeof instance.init);
  
  // Test if properties exist by checking a few key ones
  console.log('Sample properties:');
  console.log('  subnetStats:', instance.subnetStats);
  console.log('  tailscaleStatus:', instance.tailscaleStatus);
  console.log('  deviceFilter:', instance.deviceFilter);
  console.log('  viewMode:', instance.viewMode);
} else {
  console.log('ERROR: window.dashboard is not a function');
}

if (typeof window.enhancedDashboard === 'function') {
  const instance = window.enhancedDashboard();
  console.log('EnhancedDashboard instance created via alias');
  console.log('Alias works correctly');
} else {
  console.log('ERROR: window.enhancedDashboard is not a function');
}
