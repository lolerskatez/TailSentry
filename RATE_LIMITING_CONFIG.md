# ⚙️ TailSentry Rate Limiting Configuration Guide

Guide for configuring and tuning rate limiting to balance security and performance.

## 📋 Table of Contents

- [Overview](#overview)
- [Default Configuration](#default-configuration)
- [Per-Endpoint Tuning](#per-endpoint-tuning)
- [Performance vs. Security](#performance-vs-security)
- [Monitoring](#monitoring)
- [DDoS Protection](#ddos-protection)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

Rate limiting protects TailSentry from:
- **Brute force attacks**: Limiting login attempts
- **DDoS attacks**: Preventing request floods
- **API abuse**: Protecting resources
- **Resource exhaustion**: Preventing memory/CPU spikes

Rate limits are applied per endpoint and can be configured globally or individually.

### Default Rate Limits

| Endpoint | Default Limit | Window | Purpose |
|----------|---------------|--------|---------|
| `/login` | 5 requests | Per hour | Brute force protection |
| `/api/login` | 5 requests | Per hour | API brute force protection |
| `/api/sso/callback` | 10 requests | Per hour | SSO callback protection |
| `/api/*` | 100 requests | Per minute | General API protection |
| `/metrics` | 1000 requests | Per minute | Prometheus scraper |
| `/health` | Unlimited | - | Health checks |
| `/static/*` | 1000 requests | Per minute | Asset serving |

---

## 🔧 Default Configuration

### Environment Variables

Add to `.env`:

```bash
# Global rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100                    # requests per minute
RATE_LIMIT_WINDOW_SECONDS=60              # 1 minute window
RATE_LIMIT_EXEMPT_IPS=127.0.0.1,0.0.0.0   # Localhost, container gateway

# Endpoint-specific limits
RATE_LIMIT_LOGIN=5                        # login endpoint: 5/hour
RATE_LIMIT_LOGIN_WINDOW=3600              # 1 hour
RATE_LIMIT_API=100                        # /api/*: 100/min
RATE_LIMIT_METRICS=1000                   # /metrics: 1000/min
RATE_LIMIT_HEALTH=999999                  # /health: unlimited
```

### Code Configuration

In `middleware/rate_limit.py`:

```python
# Default rate limit configuration
DEFAULT_LIMITS = {
    # Endpoint patterns: (limit, window_seconds)
    '/login': (5, 3600),              # 5 per hour
    '/api/login': (5, 3600),          # 5 per hour
    '/api/sso/callback': (10, 3600),  # 10 per hour
    '/api/devices': (100, 60),        # 100 per minute
    '/api/network-stats': (60, 60),   # 60 per minute (frequent polling)
    '/metrics': (1000, 60),           # 1000 per minute
    '/health': (999999, 60),          # Unlimited
}

# Storage backend (use 'memory' for single instance, 'redis' for cluster)
RATE_LIMIT_BACKEND = 'memory'
```

---

## 🎯 Per-Endpoint Tuning

### Common Endpoints

#### Authentication Endpoints

```python
# Strict limits to prevent brute force
'/login': (5, 3600),                 # 5 attempts per hour per IP
'/api/sso/callback': (10, 3600),     # 10 SSO callbacks per hour
'/password-reset': (3, 3600),        # 3 password resets per hour
```

**Why**: Attackers commonly target auth endpoints. Strict limits force polynomial backoff.

#### API Endpoints

```python
# Query endpoints - moderate limits
'/api/devices': (100, 60),           # 100 per minute
'/api/network-stats': (60, 60),      # 60 per minute (high frequency)
'/api/audit-logs': (50, 60),         # 50 per minute

# Write endpoints - stricter limits
'/api/settings': (10, 60),           # 10 changes per minute
'/api/users': (5, 60),               # 5 user ops per minute
```

**Why**: Reads are cheaper than writes. Network stats updated frequently. Writes should be slow.

#### Monitoring Endpoints

```python
# Prometheus scraper needs high limits
'/metrics': (1000, 60),              # 1000 per minute

# Health checks unmetered
'/health': (999999, 60),             # Unlimited
```

**Why**: Monitoring should never be throttled. Health checks should always work.

### How to Set Per-Endpoint Limits

**Option 1: Environment Variables**

```bash
# Pattern: RATE_LIMIT_<ENDPOINT>=<limit>/<window>
RATE_LIMIT_LOGIN=5/3600              # 5 per hour
RATE_LIMIT_API_DEVICES=100/60        # 100 per minute
RATE_LIMIT_METRICS=1000/60           # 1000 per minute
```

**Option 2: Configuration File**

Create `rate_limits.json`:

```json
{
  "endpoints": {
    "/login": {"limit": 5, "window": 3600, "description": "Brute force protection"},
    "/api/devices": {"limit": 100, "window": 60, "description": "Device queries"},
    "/api/settings": {"limit": 10, "window": 60, "description": "Config changes"},
    "/metrics": {"limit": 1000, "window": 60, "description": "Prometheus"},
    "/health": {"limit": 999999, "window": 60, "exempt": true}
  },
  "defaults": {
    "limit": 100,
    "window": 60
  }
}
```

**Option 3: Code Configuration**

Update `middleware/rate_limit.py`:

```python
RATE_LIMITS = {
    '/login': (5, 3600),
    '/api/devices': (100, 60),
    '/api/settings': (10, 60),
    '/metrics': (1000, 60),
    '/health': (999999, 60),
}
```

---

## ⚙️ Performance vs. Security

### Security-First Configuration

For production with security priority:

```bash
# Strict limits
RATE_LIMIT_LOGIN=3/3600              # 3 logins per hour (brute force proof)
RATE_LIMIT_API_USERS=5/60            # 5 user ops per minute
RATE_LIMIT_API_SETTINGS=5/60         # 5 setting changes per minute

# Exponential backoff: After limit hit, wait longer
RATE_LIMIT_BACKOFF_ENABLED=true
RATE_LIMIT_BACKOFF_MULTIPLIER=2      # 1min, 2min, 4min, 8min...
```

**Tradeoff**: Users may experience throttling during legitimate bulk operations.

### Performance-First Configuration

For internal/trusted deployments:

```bash
# Loose limits
RATE_LIMIT_LOGIN=50/60               # 50 logins per minute
RATE_LIMIT_API_DEVICES=500/60        # 500 device queries per minute
RATE_LIMIT_API_SETTINGS=50/60        # 50 setting changes per minute

# Disable on trusted IPs
RATE_LIMIT_EXEMPT_SUBNETS=10.0.0.0/8 # Internal network
RATE_LIMIT_EXEMPT_SUBNETS=172.16.0.0/12
```

**Tradeoff**: Less protection against abuse, but faster for legitimate users.

### Balanced Configuration (Recommended)

```bash
# Medium limits
RATE_LIMIT_LOGIN=10/3600             # 10 logins per hour
RATE_LIMIT_API=100/60                # 100 API calls per minute
RATE_LIMIT_WRITES=20/60              # 20 writes per minute

# Whitelist internal/monitoring IPs
RATE_LIMIT_EXEMPT_IPS=127.0.0.1      # localhost
RATE_LIMIT_EXEMPT_IPS=prometheus:9090 # Prometheus scraper
RATE_LIMIT_EXEMPT_IPS=10.0.0.0/8     # Internal network (optional)
```

### Adjustment Flowchart

```
Current limit too low?
├─ YES → Users getting 429 errors
│   ├─ Is it sustained traffic? → Increase limit
│   └─ Is it spike traffic? → Implement burst allowance
│
└─ NO → Is security concern?
    ├─ YES → Detected brute force? → Decrease limit
    └─ NO → Keep current settings
```

---

## 📊 Monitoring

### Check Current Limits

```bash
# View current rate limit config
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/admin/rate-limits

# Response:
{
  "endpoints": {
    "/login": {"limit": 5, "window": 3600, "hits_this_window": 3},
    "/api/devices": {"limit": 100, "window": 60, "hits_this_window": 47}
  }
}
```

### Monitor Rate Limit Triggers

**Log Monitoring**:
```bash
# View rate limit violations
grep "rate_limit" /opt/tailsentry/logs/tailsentry.log

# Output:
# 2025-04-08 14:23:15 WARNING Rate limit exceeded for 192.168.1.100: /api/login (5/3600)
# 2025-04-08 14:23:16 WARNING Rate limit exceeded for 192.168.1.100: /api/login (5/3600)
```

**Prometheus Metrics**:
```promql
# Query rate limit hits
increase(tailsentry_rate_limit_exceeded_total[5m])

# Query by endpoint
increase(tailsentry_rate_limit_exceeded_total[5m]) by (endpoint)

# Query by IP
increase(tailsentry_rate_limit_exceeded_total[5m]) by (client_ip)
```

**Alert on Brute Force**:
```yaml
- alert: BruteForceAttempt
  expr: increase(tailsentry_rate_limit_exceeded_total{endpoint="/login"}[5m]) > 10
  for: 5m
  annotations:
    summary: "Brute force attempt detected on login endpoint"
```

### Identify Problematic IPs

```bash
# Find IPs hitting rate limits most
tail -f /opt/tailsentry/logs/tailsentry.log | \
  grep "rate_limit" | \
  awk '{print $NF}' | \
  sort | uniq -c | sort -rn | head -20
```

---

## 🛡️ DDoS Protection

### Defending Against DDoS

#### Level 1: IP-Based Rate Limiting (Current)

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/60
RATE_LIMIT_LOGIN=5/3600
```

#### Level 2: Add Reverse Proxy Protection (Nginx)

```nginx
# /etc/nginx/conf.d/tailsentry.conf

# Global rate limit: 1000 requests per minute
limit_req_zone $binary_remote_addr zone=global:10m rate=1000r/m;

# Login-specific limit: 5 requests per hour
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/h;

server {
  listen 8080;
  server_name _;

  # Apply global limit to all endpoints
  limit_req zone=global burst=50 nodelay;

  # Apply stricter limit to login
  location /login {
    limit_req zone=login burst=2 nodelay;
    proxy_pass http://localhost:5000;
  }

  location / {
    proxy_pass http://localhost:5000;
  }
}
```

#### Level 3: WAF/DDoS Service

For production:
- **Cloudflare**: Managed DDoS protection
- **AWS Shield**: Built into ALB/CloudFront
- **Imperva**: Enterprise DDoS mitigation
- **Akamai**: Global DDoS defense

Configuration:
```bash
# Configure Cloudflare rate limiting rules
# 1. Enable Cloudflare on your domain
# 2. Set up rate limiting rule: >100 reqs/min = Block for 10 min
# 3. Enable DDOS protection in Firewall settings
```

#### Level 4: Blackhole Routing (Extreme)

For confirmed sustained attack:
```bash
# Route attacker IPs to null
sudo ip route add 192.0.2.100/32 blackhole

# Or with iptables
sudo iptables -A INPUT -s 192.0.2.100 -j DROP
```

---

## 🔧 Troubleshooting

### Problem: Users Getting 429 Errors

**Check**:
```bash
# View rate limit logs
tail -f /opt/tailsentry/logs/tailsentry.log | grep "429"

# Check if legitimate traffic
grep "429" /opt/tailsentry/logs/tailsentry.log | tail -20
```

**Solutions**:
```bash
# Option 1: Increase limit
RATE_LIMIT_API=200/60  # Was 100/60

# Option 2: Whitelist IP
RATE_LIMIT_EXEMPT_IPS=10.0.0.0/8

# Option 3: Increase window
RATE_LIMIT_WINDOW_SECONDS=120  # Was 60
```

### Problem: Brute Force Not Being Stopped

**Check**:
```bash
# Verify rate limiting is enabled
grep "RATE_LIMIT_ENABLED" /opt/tailsentry/.env

# Check login limit
grep "RATE_LIMIT_LOGIN" /opt/tailsentry/.env

# Verify middleware is loaded
grep -i "rate_limit" /opt/tailsentry/logs/tailsentry.log | head -5
```

**Solutions**:
```bash
# Make login limit stricter
RATE_LIMIT_LOGIN=3/3600  # Was 5/3600 - 3 attempts per hour

# Enable IP-based tracking (not session)
RATE_LIMIT_BY_IP=true
RATE_LIMIT_BY_SESSION=false
```

### Problem: Prometheus Scraper Getting Blocked

**Check**:
```bash
# Is Prometheus IP exempt?
grep "RATE_LIMIT_EXEMPT_IPS" /opt/tailsentry/.env

# Test Prometheus connection
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/metrics
```

**Solution**:
```bash
# Whitelist Prometheus IP
RATE_LIMIT_EXEMPT_IPS=127.0.0.1,prometheus-server-ip
```

---

## ✅ Configuration Checklist

Before moving to production:

- [ ] Rate limiting is enabled
- [ ] Login endpoint is protected (5 or fewer per hour)
- [ ] API endpoints have reasonable limits (100+/min)
- [ ] Health check is unlimited (999999)
- [ ] Metrics endpoint is not limited (1000+/min)
- [ ] Monitoring alerts are configured
- [ ] Brute force attempt logging is enabled
- [ ] IP whitelisting is configured for internal services
- [ ] DDoS mitigation is planned (WAF, Cloudflare, etc.)

---

## 🔗 Related Documentation

- [SECURITY.md](SECURITY.md) - Overall security architecture
- [PROMETHEUS_SETUP.md](PROMETHEUS_SETUP.md) - Monitoring rate limit metrics
- [DISCORD_BOT_SECURITY.md](DISCORD_BOT_SECURITY.md) - Discord bot rate limiting
- See `middleware/rate_limit.py` for implementation details

---

## 📞 Support

### Quick Reference

```bash
# Check rate limit config
cat /opt/tailsentry/.env | grep RATE_LIMIT

# View current limits
curl http://localhost:8080/api/admin/debugrate-limits

# Clear rate limit cache (if issues)
redis-cli FLUSHDB  # If using Redis backend

# Test rate limiter
for i in {1..10}; do
  curl http://localhost:8080/login
  echo "Request $i at $(date)"
done
```

---

**Next Steps**:
1. Review default limits in your .env
2. Monitor rate limit metrics in Prometheus
3. Adjust based on observed traffic patterns
4. Implement DDoS protection for production
5. Test brute force protection quarterly

