# 📊 TailSentry Prometheus Monitoring Setup

Complete guide for setting up Prometheus monitoring of TailSentry, including metrics collection, dashboards, and alerting.

## 📋 Table of Contents

- [Overview](#overview)
- [Metrics Exposed](#metrics-exposed)
- [Prometheus Setup](#prometheus-setup)
- [Grafana Dashboard](#grafana-dashboard)
- [Alerting Rules](#alerting-rules)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

TailSentry exposes Prometheus metrics at `http://localhost:8080/metrics` for monitoring via Prometheus and visualization via Grafana.

### Supported Deployment Models

| Model | Effort | Recommended For |
|-------|--------|-----------------|
| **Local Prometheus** | Low | Development, single instance |
| **Docker Stack** | Medium | Docker deployments |
| **Kubernetes** | High | Large-scale deployments |
| **Managed Cloud** | Low | AWS CloudWatch, Azure Monitor, etc. |

---

## 📈 Metrics Exposed

TailSentry exposes the following Prometheus metrics:

### Application Metrics

```
# HELP tailsentry_app_info Application information
# TYPE tailsentry_app_info gauge
tailsentry_app_info{version="1.0.0"} 1

# HELP tailsentry_requests_total Total HTTP requests
# TYPE tailsentry_requests_total counter
tailsentry_requests_total{endpoint="/api/devices",method="GET",status="200"} 1543

# HELP tailsentry_request_duration_seconds HTTP request duration in seconds
# TYPE tailsentry_request_duration_seconds histogram
tailsentry_request_duration_seconds_bucket{endpoint="/api/devices",le="0.1"} 1200
tailsentry_request_duration_seconds_bucket{endpoint="/api/devices",le="1.0"} 1500

# HELP tailsentry_requests_in_progress Number of requests in progress
# TYPE tailsentry_requests_in_progress gauge
tailsentry_requests_in_progress 3
```

### Device Metrics

```
# HELP tailsentry_devices_total Total Tailscale devices
# TYPE tailsentry_devices_total gauge
tailsentry_devices_total 24

# HELP tailsentry_devices_online Online Tailscale devices
# TYPE tailsentry_devices_online gauge
tailsentry_devices_online 21

# HELP tailsentry_devices_offline Offline Tailscale devices
# TYPE tailsentry_devices_offline gauge
tailsentry_devices_offline 3

# HELP tailsentry_exit_nodes_active Active exit nodes
# TYPE tailsentry_exit_nodes_active gauge
tailsentry_exit_nodes_active 2
```

### Network Metrics

```
# HELP tailsentry_network_bytes_sent Bytes sent over network per device
# TYPE tailsentry_network_bytes_sent gauge
tailsentry_network_bytes_sent{device="laptop"} 1073741824

# HELP tailsentry_network_bytes_received Bytes received over network per device
# TYPE tailsentry_network_bytes_received gauge
tailsentry_network_bytes_received{device="laptop"} 536870912

# HELP tailsentry_network_latency_ms Network latency in milliseconds
# TYPE tailsentry_network_latency_ms gauge
tailsentry_network_latency_ms{device="server1"} 45
```

### Database Metrics

```
# HELP tailsentry_db_queries_total Total database queries
# TYPE tailsentry_db_queries_total counter
tailsentry_db_queries_total{operation="select"} 50000

# HELP tailsentry_db_errors_total Total database errors
# TYPE tailsentry_db_errors_total counter
tailsentry_db_errors_errors_total 5
```

### Authentication Metrics

```
# HELP tailsentry_logins_total Total login attempts
# TYPE tailsentry_logins_total counter
tailsentry_logins_total{status="success"} 1200
tailsentry_logins_total{status="failed"} 15

# HELP tailsentry_active_sessions Active user sessions
# TYPE tailsentry_active_sessions gauge
tailsentry_active_sessions 8

# HELP tailsentry_sso_authentications_total SSO authentication attempts
# TYPE tailsentry_sso_authentications_total counter
tailsentry_sso_authentications_total{provider="google",status="success"} 450
```

### System Metrics

```
# HELP tailsentry_memory_bytes Memory usage in bytes
# TYPE tailsentry_memory_bytes gauge
tailsentry_memory_bytes 134217728

# HELP tailsentry_cpu_seconds_total CPU seconds consumed
# TYPE tailsentry_cpu_seconds_total counter
tailsentry_cpu_seconds_total 3600

# HELP tailsentry_uptime_seconds Application uptime in seconds
# TYPE tailsentry_uptime_seconds gauge
tailsentry_uptime_seconds 604800
```

**View all metrics**: `curl http://localhost:8080/metrics`

---

## 🔧 Prometheus Setup

### Quick Start: Docker Compose

Create `docker-compose.monitoring.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin123
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
```

### Configuration: Prometheus Config File

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s              # Default scrape interval
  evaluation_interval: 15s          # Evaluate alerts every 15 seconds
  external_labels:
    monitor: 'tailsentry-monitor'

# Alertmanager configuration (optional)
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

# Load rules once
rule_files:
  - 'alert_rules.yml'

scrape_configs:
  # TailSentry metrics
  - job_name: 'tailsentry'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
    
    # Optional: Basic auth if TailSentry requires authentication
    # basic_auth:
    #   username: 'prometheus'
    #   password: 'secret_password'
    
    # Relabel configs for custom labels
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'tailsentry-primary'
  
  # If you have multiple TailSentry instances
  - job_name: 'tailsentry-standby'
    static_configs:
      - targets: ['tailsentry-standby.company.com:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # (Optional) Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Start Monitoring Stack

```bash
# Start with Docker Compose
docker-compose -f docker-compose.monitoring.yml up -d

# Verify Prometheus is collecting metrics
curl http://localhost:9090/api/v1/targets

# Access Prometheus dashboard
# http://localhost:9090

# Access Grafana
# http://localhost:3000 (admin/admin123)
```

### Linux Systemd Setup

**Install Prometheus**:
```bash
# Download
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xzf prometheus-2.45.0.linux-amd64.tar.gz
sudo mv prometheus-2.45.0.linux-amd64 /opt/prometheus

# Create systemd service
sudo tee /etc/systemd/system/prometheus.service > /dev/null <<EOF
[Unit]
Description=Prometheus
After=network.target

[Service]
Type=simple
User=prometheus
WorkingDirectory=/opt/prometheus
ExecStart=/opt/prometheus/prometheus \
  --config.file=/opt/prometheus/prometheus.yml \
  --storage.tsdb.path=/opt/prometheus/data
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

---

## 📊 Grafana Dashboard

### Create Custom Dashboard

**Dashboard JSON** (import via Grafana UI):

```json
{
  "dashboard": {
    "title": "TailSentry Monitoring",
    "panels": [
      {
        "title": "Devices Online",
        "targets": [
          {
            "expr": "tailsentry_devices_online",
            "legendFormat": "Online"
          }
        ],
        "type": "graph",
        "gridPos": {"x": 0, "y": 0, "w": 8, "h": 8}
      },
      {
        "title": "Requests Per Second",
        "targets": [
          {
            "expr": "rate(tailsentry_requests_total[1m])",
            "legendFormat": "{{ endpoint }}"
          }
        ],
        "type": "graph",
        "gridPos": {"x": 8, "y": 0, "w": 8, "h": 8}
      },
      {
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "tailsentry_memory_bytes / 1024 / 1024",
            "legendFormat": "MB"
          }
        ],
        "type": "graph",
        "gridPos": {"x": 16, "y": 0, "w": 8, "h": 8}
      },
      {
        "title": "API Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(tailsentry_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ],
        "type": "graph",
        "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8}
      },
      {
        "title": "Failed Logins",
        "targets": [
          {
            "expr": "rate(tailsentry_logins_total{status=\"failed\"}[5m])",
            "legendFormat": "Failed Logins/sec"
          }
        ],
        "type": "graph",
        "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8}
      }
    ]
  }
}
```

**Import Steps**:
1. Navigate to Grafana: http://localhost:3000
2. Click "+" → "Import"
3. Paste JSON above
4. Select Prometheus as datasource
5. Click "Import"

### Pre-built Dashboards

Download from Grafana dashboard repository:
- [FastAPI Monitoring](https://grafana.com/grafana/dashboards/12114) - FastAPI-specific dashboard
- [Application Metrics](https://grafana.com/grafana/dashboards/12578) - Generic app metrics
- [System Metrics](https://grafana.com/grafana/dashboards/1860) - Linux system metrics

---

## ⚠️ Alerting Rules

Create `alert_rules.yml`:

```yaml
groups:
  - name: tailsentry_alerts
    interval: 30s
    rules:
      # Device offline alert
      - alert: DeviceOffline
        expr: tailsentry_devices_offline > 5
        for: 5m
        annotations:
          summary: "{{ $value }} devices offline"
          description: "More than 5 TailSentry devices are offline"

      # High API latency
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(tailsentry_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        annotations:
          summary: "High API response time: {{ $value }}s"
          description: "API p95 latency exceeds 2 seconds"

      # High memory usage
      - alert: HighMemoryUsage
        expr: tailsentry_memory_bytes / (1024 * 1024) > 512
        for: 10m
        annotations:
          summary: "High memory: {{ $value }}MB"
          description: "TailSentry using more than 512MB RAM"

      # Database errors increasing
      - alert: DatabaseErrors
        expr: increase(tailsentry_db_errors_total[5m]) > 10
        for: 5m
        annotations:
          summary: "{{ $value }} database errors in 5 minutes"
          description: "Spike in database errors detected"

      # Login failures
      - alert: SuspiciousLoginActivity
        expr: rate(tailsentry_logins_total{status="failed"}[5m]) > 0.5
        for: 5m
        annotations:
          summary: "Failed login rate: {{ $value }}/sec"
          description: "High rate of failed login attempts detected"

      # Service down
      - alert: TailSentryDown
        expr: up{job="tailsentry"} == 0
        for: 1m
        annotations:
          summary: "TailSentry service is down"
          description: "TailSentry is not responding on metrics endpoint"

      # High request rate (possible DDoS)
      - alert: HighRequestRate
        expr: rate(tailsentry_requests_total[1m]) > 1000
        for: 5m
        annotations:
          summary: "{{ $value }} requests/sec"
          description: "Unusually high request rate detected"
```

### Alert Notification Channels

**Configure in Prometheus** (via AlertManager):

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h

receivers:
  - name: 'default'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK'
        channel: '#alerts'
        title: 'TailSentry Alert'
        text: '{{ .GroupLabels.alertname }}'
```

---

## 🔧 Troubleshooting

### Problem: Prometheus Can't Connect to TailSentry

**Check**:
```bash
# Test endpoint
curl http://localhost:8080/metrics

# Check firewall
sudo ufw status
sudo firewall-cmd --list-all

# Check TailSentry is running
systemctl status tailsentry
```

### Problem: No Metrics Being Collected

**Check**:
```bash
# Verify Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check for scrape errors
curl http://localhost:9090/api/v1/query?query=up

# Review Prometheus logs
docker logs $(docker ps -q --filter ancestor=prom/prometheus)
```

### Problem: High Prometheus Disk Usage

**Solution**:
```yaml
# In prometheus.yml, reduce retention:
command:
  - '--storage.tsdb.retention.time=7d'  # Instead of 30d
```

### Problem: Missing Metrics

**Verify**:
1. Metrics endpoint is accessible: `curl http://localhost:8080/metrics`
2. TailSentry version supports metrics (check logs)
3. Metrics middleware is enabled in TailSentry config
4. Prometheus has permission to scrape

---

## 📞 Support

### Documentation
- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/grafana)
- [Dashboard Library](https://grafana.com/grafana/dashboards)

### Quick Commands

```bash
# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=tailsentry_devices_online'

# Export metrics
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Prometheus is collecting metrics (check targets page)
- [ ] Grafana dashboard displays data
- [ ] Alert rules are loaded (check Prometheus alerts page)
- [ ] Slack/email notifications are working
- [ ] Retention policy is set appropriately
- [ ] Backup/restore of Prometheus data is documented

---

## 🔗 Related Documentation

- [DATABASE_BACKUP.md](DATABASE_BACKUP.md) - Back up Prometheus time-series data
- [MONITORING.md](MONITORING.md) *(Phase 3)* - Operational monitoring guide
- [RATE_LIMITING_CONFIG.md](RATE_LIMITING_CONFIG.md) *(Phase 3)* - Rate limiting info

---

**Next Steps**:
1. Deploy Prometheus and Grafana
2. Import TailSentry dashboard
3. Configure alert rules
4. Set up notification channels
5. Test alerts
6. Document runbooks for common alerts

