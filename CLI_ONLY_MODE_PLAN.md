# TailSentry CLI-Only Mode Implementation Plan

## Security-First Approach

### Problem Statement
Exit nodes with API Access Tokens pose a significant security risk - if compromised, attackers could:
- Create/revoke auth keys → Add rogue devices
- Access entire tailnet device list → Network reconnaissance  
- Modify network policies → Traffic manipulation

### Solution: CLI-Only Mode

#### Phase 1: Detect and Adapt
- Auto-detect if API Access Token is available
- Gracefully fall back to CLI-only mode when API is unavailable
- Display appropriate UI based on available features

#### Phase 2: Feature Matrix

**✅ CLI-Only Mode (Secure for Exit Nodes):**
- Device status and configuration
- Peer visibility (all devices in tailnet)
- Exit node management (this device)
- Route advertisement (this device)
- Network topology view
- Basic monitoring and metrics

**🔒 API Mode Only (Administrative Features):**
- Auth key creation/revocation
- Cross-device management
- Advanced network policies
- Detailed device history

#### Phase 3: Implementation

**Backend Changes:**
1. Modify `/api/status` to work without API token
2. Update device list endpoint to use local daemon data
3. Add "mode" indicator to dashboard data
4. Graceful degradation for API-dependent features

**Frontend Changes:**
1. Add "Secure Mode" indicator
2. Hide/disable API-dependent features
3. Update messaging to explain limitations
4. Maintain full functionality for local device management

#### Phase 4: Security Benefits

**For Exit Nodes:**
- No API token stored → No network-wide compromise if breached
- Full local device management capability
- Complete network visibility via local daemon
- 90% of TailSentry functionality with 10% of the risk

**For Administrative Nodes:**
- Full API mode available for management tasks
- Centralized auth key management
- Network-wide device control

## Implementation Priority

1. **High Priority:** Basic CLI-only mode with device status
2. **Medium Priority:** Peer management via local daemon
3. **Low Priority:** Advanced features and UI polish

This approach provides the best of both worlds - security for exit nodes and full functionality for administrative nodes.
