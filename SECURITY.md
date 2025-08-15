# 🔒 TailSentry Security Checklist

## 📋 Pre-Deployment Security Checklist

### ✅ Environment & Secrets
- [ ] `.env` file removed from repository (should not be tracked)
- [ ] `.env.example` contains no sensitive data
- [ ] SESSION_SECRET generated with cryptographically secure random values
- [ ] ADMIN_PASSWORD_HASH created with bcrypt (never plain text)
- [ ] Tailscale PAT stored securely (not in code)
- [ ] All secrets use environment variables, never hardcoded

### ✅ File Permissions & Access
- [ ] `.gitignore` properly excludes all sensitive files
- [ ] Log files excluded from version control
- [ ] Data directories excluded from version control
- [ ] SSL certificates and private keys excluded
- [ ] Backup files excluded from repository

### ✅ Repository Hygiene
- [ ] No credentials in commit history
- [ ] No API keys in any committed files
- [ ] No database files in repository
- [ ] No temporary files with sensitive data
- [ ] All placeholder values in example files

### ✅ Production Deployment
- [ ] Change default admin credentials
- [ ] Use strong, unique passwords
- [ ] Enable firewall (UFW/firewalld)
- [ ] Restrict access to Tailscale network only
- [ ] Use HTTPS with reverse proxy
- [ ] Enable fail2ban or similar intrusion protection
- [ ] Regular security updates scheduled

### ✅ Network Security
- [ ] TailSentry only accessible via Tailscale
- [ ] No public internet exposure
- [ ] Proper firewall rules configured
- [ ] SSL/TLS certificates valid
- [ ] Security headers enabled

## 🚨 Common Security Mistakes

### ❌ Don't Do This:
```bash
# NEVER commit real credentials
ADMIN_PASSWORD_HASH=actual_bcrypt_hash_here
SESSION_SECRET=real_secret_key_here
TAILSCALE_PAT=tskey-api-actual_token_here
```

### ✅ Do This Instead:
```bash
# Safe example template
ADMIN_PASSWORD_HASH=
SESSION_SECRET=
TAILSCALE_PAT=
```

## 🔧 Security Commands

### Generate Secure Password Hash:
```bash
python3 -c "import bcrypt; password=input('Enter password: '); print(bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())"
```

### Generate Session Secret:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Check for Secrets in Git History:
```bash
git log --all --full-history -- .env
git log -p --all | grep -i "password\|secret\|key\|token"
```

### Clean Git History (if secrets were committed):
```bash
# Remove file from all history (DESTRUCTIVE)
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env' --prune-empty --tag-name-filter cat -- --all
```

## 📞 Security Incident Response

If you accidentally commit secrets:

1. **Immediately rotate all exposed credentials**
2. **Remove secrets from git history**
3. **Force push cleaned history**
4. **Notify team members to re-clone repository**
5. **Update deployment with new credentials**

## 🛡️ Additional Security Resources

- [OWASP Application Security](https://owasp.org/www-project-application-security-verification-standard/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [Tailscale Security Model](https://tailscale.com/security/)
- [Python Security Guidelines](https://python-security.readthedocs.io/)

---

**Remember**: Security is everyone's responsibility! 🔐
