# TailSentry Development & Operations Guide

Master documentation guide for TailSentry developers, operators, and contributors. This document organizes all project guides and provides a single entry point for project information.

> **Last Updated**: April 2026  
> **Project Status**: Production-Ready  
> **Version**: See `version.py` for current version

---

## 📚 Quick Navigation

### 🚀 Getting Started
- [README.md](README.md) — Project overview, features, quick installation
- [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) — Comprehensive installation & setup

### 🏗️ Deployment & Architecture
- [DEPLOYMENT.md](DEPLOYMENT.md) — Deployment options (Docker, Linux, Windows)
- [LINUX_DEPLOYMENT.md](LINUX_DEPLOYMENT.md) — Linux-specific deployment procedures
- [WINDOWS_COMPATIBILITY_IMPLEMENTATION_PLAN.md](WINDOWS_COMPATIBILITY_IMPLEMENTATION_PLAN.md) — Windows support details

### 🔐 Security & Hardening
- [SECURITY.md](SECURITY.md) — Security architecture and best practices
- [SECURITY_COMPARTMENTALIZATION.md](SECURITY_COMPARTMENTALIZATION.md) — Security design patterns
- [SMTP_SECURITY_ANALYSIS.md](SMTP_SECURITY_ANALYSIS.md) — Email security configuration

### 🤖 Discord Bot Integration
- [DISCORD_BOT_DOCUMENTATION.md](DISCORD_BOT_DOCUMENTATION.md) — Complete Discord bot guide
- [DISCORD_BOT_SETUP.md](DISCORD_BOT_SETUP.md) — Bot installation & configuration
- [DISCORD_BOT_SECURITY.md](DISCORD_BOT_SECURITY.md) — Bot security considerations
- [DISCORD_BOT_TROUBLESHOOTING.md](DISCORD_BOT_TROUBLESHOOTING.md) — Common Discord bot issues

### 🔑 Authentication & Access Control
- [SSO_SETUP_GUIDE.md](SSO_SETUP_GUIDE.md) — SSO/OIDC configuration (primary reference)
- [SSO_PROVIDER_COMPATIBILITY.md](SSO_PROVIDER_COMPATIBILITY.md) — Supported SSO providers
- [SSO_QUICK_REFERENCE.md](SSO_QUICK_REFERENCE.md) — Quick SSO setup reference
- [RBAC_DESIGN.md](RBAC_DESIGN.md) — Role-based access control architecture

### 🔗 Integration & Core Features
- [TAILSCALE_INTEGRATION.md](TAILSCALE_INTEGRATION.md) — Tailscale API & CLI integration
- [NOTIFICATIONS.md](NOTIFICATIONS.md) — Notification system (email alerts, device notifications)

### 📊 Operations & Monitoring
- [MONITORING.md](MONITORING.md) *(coming in Phase 3)* — Operational monitoring guide
- [DATABASE_BACKUP.md](DATABASE_BACKUP.md) — Backup automation for SQLite database
- [DATABASE_RECOVERY.md](DATABASE_RECOVERY.md) — Database corruption recovery procedures
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) — Full RTO/RPO recovery procedures and runbooks
- [PROMETHEUS_SETUP.md](PROMETHEUS_SETUP.md) — Prometheus monitoring setup and alerting
- [RATE_LIMITING_CONFIG.md](RATE_LIMITING_CONFIG.md) — Rate limiting tuning and DDoS protection

---

## 📋 Documentation Organization

### By Use Case

#### **I want to install TailSentry**
1. Start with [README.md](README.md) for overview
2. Follow [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for step-by-step instructions
3. Choose deployment: [DEPLOYMENT.md](DEPLOYMENT.md) for Docker/Linux options

#### **I want to set up Discord notifications**
1. [DISCORD_BOT_SETUP.md](DISCORD_BOT_SETUP.md) — Installation & token setup
2. [DISCORD_BOT_DOCUMENTATION.md](DISCORD_BOT_DOCUMENTATION.md) — Commands & features
3. [DISCORD_BOT_TROUBLESHOOTING.md](DISCORD_BOT_TROUBLESHOOTING.md) — If issues arise

#### **I want to configure SSO (Active Directory, Google, GitHub, etc.)**
1. [SSO_SETUP_GUIDE.md](SSO_SETUP_GUIDE.md) — Detailed configuration walkthrough
2. [SSO_PROVIDER_COMPATIBILITY.md](SSO_PROVIDER_COMPATIBILITY.md) — Check your provider is supported
3. [SSO_QUICK_REFERENCE.md](SSO_QUICK_REFERENCE.md) — Quick lookup for common settings

#### **I want to understand security architecture**
1. [SECURITY.md](SECURITY.md) — Overall security strategy
2. [SECURITY_COMPARTMENTALIZATION.md](SECURITY_COMPARTMENTALIZATION.md) — Security design
3. [RBAC_DESIGN.md](RBAC_DESIGN.md) — User permissions architecture

#### **I want to operate TailSentry in production**
1. [DEPLOYMENT.md](DEPLOYMENT.md) — Choose deployment model
2. [MONITORING.md](MONITORING.md) *(Phase 3)* — Set up operational monitoring
3. [DATABASE_BACKUP.md](DATABASE_BACKUP.md) *(Phase 2)* — Configure automated backups
4. [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) *(Phase 2)* — Plan disaster recovery

#### **I want to integrate with Tailscale**
1. [TAILSCALE_INTEGRATION.md](TAILSCALE_INTEGRATION.md) — Integration architecture
2. [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md#tailscale-setup) — Tailscale prerequisites

#### **I need to set up email notifications**
1. [NOTIFICATIONS.md](NOTIFICATIONS.md) — Notification system overview
2. [SMTP_SECURITY_ANALYSIS.md](SMTP_SECURITY_ANALYSIS.md) — Secure SMTP configuration

---

## 🔧 Configuration Files Reference

| File | Purpose | Location |
|------|---------|----------|
| `.env` | Environment variables (secrets, API keys) | Project root |
| `tailsentry_config.json` | Application configuration | `config/` |
| `tailscale_settings.json` | Tailscale integration settings | `config/` |
| `users.db` | SQLite user database | Project root |
| `logrotate.conf` | Log rotation configuration | Project root |
| `tailsentry.service` | Systemd service file | Project root |
| `docker-compose.yml` | Development Docker setup | Project root |
| `docker-compose.prod.yml` | Production Docker setup | Project root |

---

## 📁 Project Structure

```
TailSentry/
├── main.py                      # Application entry point
├── version.py                   # Version information
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Python project metadata
│
├── routes/                      # API endpoints & routes
│   ├── api.py                  # REST API endpoints
│   ├── authenticate.py         # Authentication routes
│   ├── dashboard.py            # Dashboard UI
│   ├── config.py               # Configuration endpoints
│   ├── monitoring.py           # Monitoring/metrics
│   ├── tailscale.py            # Tailscale operations
│   ├── exit_node.py            # Exit node management
│   ├── sso.py                  # SSO integration
│   ├── discord.py              # Discord bot webhook
│   ├── notifications.py        # Notification endpoints
│   └── ...
│
├── middleware/                  # Cross-cutting concerns
│   ├── security.py             # Security headers
│   ├── csrf.py                 # CSRF protection
│   ├── rate_limit.py           # Rate limiting
│   ├── metrics.py              # Metrics tracking
│   ├── monitoring.py           # Health monitoring
│   └── smtp_security.py        # SMTP configuration
│
├── services/                    # Business logic layer
│   ├── tailscale_service.py    # Tailscale operations
│   ├── notification_service.py # Email/notification sending
│   ├── device_service.py       # Device management
│   └── ...
│
├── static/                      # Frontend assets
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/                   # HTML templates (Jinja2)
│   ├── dashboard.html
│   ├── login.html
│   ├── settings.html
│   └── ...
│
├── config/                      # Configuration files
│   ├── tailsentry_config.json
│   ├── tailscale_settings.json
│   └── ...
│
├── data/                        # Data storage
│   └── acl_backups/            # Tailscale ACL backups
│
├── logs/                        # Application logs
│
└── scripts/                     # Utility scripts
    ├── setup.sh                # Installation script
    ├── security_hardening.sh   # Security setup
    └── ...
```

---

## 🎯 Common Tasks

### Installation & Setup
```bash
# Interactive installation (recommended)
sudo ./setup.sh

# Docker deployment
docker-compose -f docker-compose.prod.yml up -d

# Manual installation
pip install -r requirements.txt
python main.py
```

### Configuration
Edit `.env` file with:
- `TAILSCALE_API_TOKEN` — Tailscale API authentication
- `DISCORD_BOT_TOKEN` — Discord bot token
- `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` — SSO credentials
- `SMTP_*` — Email configuration

### Monitoring
- Check logs: `tail -f logs/tailsentry.log`
- System status: `systemctl status tailsentry` (if installed as service)
- Health endpoint: `curl http://localhost:8080/health`

### Backup
```bash
# Backup database
cp data/users.db data/users.db.backup-$(date +%Y%m%d)

# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/
```

---

## 📞 Support & Troubleshooting

### Quick Links
- **General Install Issues**: See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md#troubleshooting)
- **Discord Bot Issues**: See [DISCORD_BOT_TROUBLESHOOTING.md](DISCORD_BOT_TROUBLESHOOTING.md)
- **SSO Setup Issues**: See [SSO_SETUP_GUIDE.md](SSO_SETUP_GUIDE.md) or [SSO_QUICK_REFERENCE.md](SSO_QUICK_REFERENCE.md)
- **Linux-Specific Issues**: See [LINUX_DEPLOYMENT.md](LINUX_DEPLOYMENT.md)
- **Windows Support**: See [WINDOWS_COMPATIBILITY_IMPLEMENTATION_PLAN.md](WINDOWS_COMPATIBILITY_IMPLEMENTATION_PLAN.md)

### Logging
- Application logs: `logs/tailsentry.log`
- Systemd logs: `journalctl -u tailsentry -f`
- Docker logs: `docker-compose logs -f`

### Debug Mode
Enable debug logging in `.env`:
```
DEBUG=true
LOG_LEVEL=DEBUG
```

---

## 📚 Additional Resources

- **GitHub Repository**: [lolerskatez/TailSentry](https://github.com/lolerskatez/TailSentry)
- **Tailscale Documentation**: [tailscale.com/docs](https://tailscale.com/docs)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Discord Bot Developer**: [discord.com/developers](https://discord.com/developers)

---

## 🚀 Version & Changelog

Current version: See [version.py](version.py)

For implementation history and feature timeline, see [FEATURES_LOG.md](FEATURES_LOG.md) *(coming in Phase 1)*

---

## 📝 Contributing

When adding new documentation:
1. Add file to appropriate section above
2. Update this document's navigation
3. Follow markdown formatting standards
4. Include table of contents for files > 500 lines

See [CONSOLIDATION_CLEANUP_NOTES.md](CONSOLIDATION_CLEANUP_NOTES.md) for recent documentation consolidation work and cleanup recommendations.

---

**Need help?** Check the relevant section above, or review the troubleshooting section in [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md).
