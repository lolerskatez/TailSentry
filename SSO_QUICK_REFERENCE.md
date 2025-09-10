# 🚀 SSO Quick Reference - TailSentry

## 📋 Provider Quick Setup

### Google Workspace
```yaml
Provider Name: Google Workspace
Issuer URL: https://accounts.google.com
Scopes: openid email profile
Group Claim: groups (requires Google Admin SDK)
```

### Microsoft Entra ID (Azure AD)
```yaml
Provider Name: Microsoft Entra ID
Issuer URL: https://login.microsoftonline.com/{tenant-id}/v2.0
Scopes: openid email profile
Group Claim: groups
```

### Authentik
```yaml
Provider Name: Authentik
Issuer URL: https://auth.company.com/application/o/tailsentry/
Scopes: openid email profile
Group Claim: groups
```

### Keycloak
```yaml
Provider Name: Keycloak
Issuer URL: https://auth.company.com/realms/master
Scopes: openid email profile
Group Claim: realm_access.roles
```

### Okta
```yaml
Provider Name: Okta
Issuer URL: https://dev-123456.okta.com/oauth2/default
Scopes: openid email profile groups
Group Claim: groups
```

### Auth0
```yaml
Provider Name: Auth0
Issuer URL: https://your-domain.auth0.com
Scopes: openid email profile
Group Claim: https://company.com/roles
```

## 🔧 Common Role Mappings

### Simple Mapping
```json
{
  "admins": "admin",
  "users": "user",
  "guests": "readonly"
}
```

### Department-Based
```json
{
  "IT Department": "admin",
  "Engineering": "user",
  "Management": "user",
  "Contractors": "readonly"
}
```

### Group-Based (Keycloak/LDAP)
```json
{
  "tailsentry-admin": "admin",
  "tailsentry-user": "user",
  "tailsentry-readonly": "readonly",
  "domain-admins": "admin"
}
```

## 🏃‍♂️ 5-Minute Setup Checklist

- [ ] Enable SSO in TailSentry settings
- [ ] Create OAuth app in your identity provider
- [ ] Copy redirect URI from TailSentry to provider
- [ ] Enter issuer URL and click "Discover"
- [ ] Add client ID and secret
- [ ] Configure role mappings (optional)
- [ ] Test login with SSO provider
- [ ] Verify user role assignment

## 🔗 Quick Links

- **TailSentry SSO Settings**: `http://your-server:8080/settings/sso`
- **Google Cloud Console**: https://console.cloud.google.com/
- **Azure Portal**: https://portal.azure.com/
- **Okta Admin Console**: https://dev-123456-admin.okta.com/
- **Auth0 Dashboard**: https://manage.auth0.com/

## 🆘 Emergency Access

If SSO is misconfigured and you're locked out:

1. **Direct Admin Login**: `http://your-server:8080/login` (use local admin account)
2. **Disable SSO**: In database or config file
3. **Reset Configuration**: Delete SSO providers from admin panel

## 📱 Testing Commands

```bash
# Test OIDC Discovery
curl https://your-issuer/.well-known/openid-configuration

# Validate JWT Token
echo "your-jwt-token" | base64 -d

# Check TailSentry Logs
tail -f /path/to/logs/tailsentry.log | grep SSO
```
