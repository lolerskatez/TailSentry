# 🔐 SSO Provider Compatibility - TailSentry

## ✅ Tested & Verified Providers

### Cloud Providers
| Provider | Status | Auto-Discovery | Role Mapping | Notes |
|----------|--------|----------------|--------------|-------|
| **Google Workspace** | ✅ Tested | ✅ Yes | ✅ Yes | Requires Admin SDK for groups |
| **Microsoft Entra ID** | ✅ Tested | ✅ Yes | ✅ Yes | Azure AD tenant required |
| **Okta** | ✅ Tested | ✅ Yes | ✅ Yes | Full OIDC compliance |
| **Auth0** | ✅ Tested | ✅ Yes | ✅ Yes | Custom domain recommended |
| **OneLogin** | 🟡 Compatible | ✅ Yes | ✅ Yes | Not tested, should work |

### Self-Hosted / Open Source
| Provider | Status | Auto-Discovery | Role Mapping | Notes |
|----------|--------|----------------|--------------|-------|
| **Authentik** | ✅ Tested | ✅ Yes | ✅ Yes | Excellent OIDC support |
| **Keycloak** | ✅ Tested | ✅ Yes | ✅ Yes | Full feature compatibility |
| **FusionAuth** | 🟡 Compatible | ✅ Yes | ✅ Yes | OIDC compliant |
| **Dex** | 🟡 Compatible | ✅ Yes | ❌ Limited | Simple OIDC proxy |
| **Zitadel** | 🟡 Compatible | ✅ Yes | ✅ Yes | Modern OIDC provider |

### Enterprise
| Provider | Status | Auto-Discovery | Role Mapping | Notes |
|----------|--------|----------------|--------------|-------|
| **ADFS** | 🟡 Compatible | ❌ Manual | ✅ Yes | Requires manual endpoints |
| **Ping Identity** | 🟡 Compatible | ✅ Yes | ✅ Yes | Enterprise features |
| **AWS Cognito** | 🟡 Compatible | ✅ Yes | ✅ Yes | User pools required |
| **GitLab** | 🟡 Compatible | ✅ Yes | ❌ Limited | OAuth2 only |
| **GitHub** | 🟡 Compatible | ❌ No | ❌ No | OAuth2, limited claims |

## 🔧 Configuration Requirements

### Minimum OIDC Support
- OpenID Connect Discovery (`.well-known/openid-configuration`)
- Authorization Code flow
- Standard claims: `sub`, `email`, `name`
- HTTPS endpoints

### Enterprise Features
- Group/Role claims in JWT tokens
- Custom claim namespaces
- JWKS for token verification
- Refresh token support

## 🏆 Recommended Providers

### For Small Teams (1-50 users)
1. **Google Workspace** - Easy setup, reliable
2. **Authentik** - Self-hosted, feature-rich
3. **Auth0** - Managed service, good free tier

### For Medium Teams (50-500 users)
1. **Okta** - Enterprise features, excellent support
2. **Microsoft Entra ID** - Deep Office 365 integration
3. **Keycloak** - Self-hosted, highly customizable

### For Large Enterprise (500+ users)
1. **Microsoft Entra ID** - Enterprise-grade scale
2. **Okta** - Advanced security features
3. **Ping Identity** - Government/compliance focus

## 🔍 Testing Methodology

### Automated Tests
- OIDC discovery endpoint validation
- Token exchange and validation
- Claims extraction and mapping
- Role assignment verification

### Manual Verification
- User login flow
- Group/role claim processing
- Error handling and edge cases
- Security token validation

## 📋 Compatibility Checklist

Before configuring a new provider, verify:

- [ ] Supports OpenID Connect 1.0
- [ ] Has `.well-known/openid-configuration` endpoint
- [ ] Supports `authorization_code` flow
- [ ] Returns `sub`, `email` claims
- [ ] HTTPS-only endpoints
- [ ] Valid SSL certificates

### Optional Features
- [ ] Group/role claims for RBAC
- [ ] Custom claim namespaces
- [ ] Token refresh support
- [ ] JWKS for signature verification

## 🚨 Known Limitations

### Provider-Specific Issues
- **ADFS**: No auto-discovery, manual endpoint configuration required
- **GitHub**: Limited OIDC support, no group claims
- **GitLab**: Groups in separate API call, not in tokens
- **Dex**: Minimal claims, primarily a proxy

### TailSentry Limitations
- Single SSO provider active at a time
- No SAML support (OIDC/OAuth2 only)
- Group claims must be in JWT tokens (no API calls)
- Role mappings are case-sensitive

## 🔮 Future Support

### Planned Providers
- **Cisco Duo** - MFA integration
- **JumpCloud** - Directory service
- **CyberArk** - Privileged access

### Feature Roadmap
- Multiple SSO provider support
- Just-in-time (JIT) user provisioning
- Advanced role mapping rules
- SAML 2.0 support

## 🆘 Getting Help

### If Your Provider Isn't Listed
1. Check if it supports OpenID Connect 1.0
2. Try the generic OIDC configuration
3. Test with manual endpoint configuration
4. Check provider documentation for OIDC compliance

### Common Issues
- **Discovery fails**: Use manual endpoint configuration
- **No groups**: Check provider's group claim configuration
- **Invalid tokens**: Verify client ID/secret and scopes
- **Role mapping fails**: Ensure JSON syntax is correct

### Support Resources
- [SSO Setup Guide](SSO_SETUP_GUIDE.md) - Detailed configuration
- [SSO Quick Reference](SSO_QUICK_REFERENCE.md) - Quick setup
- Provider documentation links in setup guide
- TailSentry logs for debugging information

---

*Last updated: September 2025*
*Testing performed on TailSentry v1.0.0+*
