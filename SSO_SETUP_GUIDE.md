# 🔐 SSO Setup Guide - TailSentry

Complete guide for configuring Single Sign-On (SSO) with enterprise identity providers.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Setup](#quick-setup)
- [Supported Providers](#supported-providers)
- [Provider-Specific Guides](#provider-specific-guides)
- [Advanced Configuration](#advanced-configuration)
- [Role Mapping](#role-mapping)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

TailSentry's SSO system supports any OIDC/OAuth2 compliant identity provider through:

- **🚀 Auto-Discovery**: Automatic endpoint discovery from issuer URLs
- **🏢 Enterprise Ready**: Support for role mapping and group claims
- **🔧 Flexible**: Manual endpoint configuration for custom setups
- **🎨 User-Friendly**: Intuitive admin interface for provider management

## ✅ Prerequisites

1. **Admin Access**: You must be logged in as an admin user
2. **Identity Provider**: Access to configure OAuth2/OIDC applications
3. **Network Access**: TailSentry must reach your identity provider
4. **Valid Certificates**: HTTPS endpoints with valid SSL certificates

## 🚀 Quick Setup

### Step 1: Enable SSO
1. Navigate to **Settings** → **SSO Settings**
2. Check **"Enable SSO Authentication"**
3. Click **"Save Changes"**

### Step 2: Add Provider
1. Click **"Add Provider"** button
2. Fill in the **Basic Configuration**:
   - Provider Name (e.g., "Google Workspace", "Authentik")
   - Logo URL (optional)
   - Enable checkbox

### Step 3: Configure OAuth
1. Enter **Client ID** and **Client Secret** from your provider
2. Copy the **Redirect URI** to your OAuth application

### Step 4: Auto-Discovery (Recommended)
1. Enter your **Issuer URL** (e.g., `https://auth.company.com/realms/master`)
2. Click **"Discover"** to auto-populate endpoints
3. Skip to Step 6 if discovery succeeds

### Step 5: Manual Endpoints (if needed)
If auto-discovery fails, manually enter:
- Authorization Endpoint
- Token Endpoint
- User Info Endpoint
- JWKS URI (optional)

### Step 6: Save and Test
1. Click **"Add Provider"**
2. Test login with the new provider

## 🏢 Supported Providers

### Cloud Providers
- **Google Workspace** - `https://accounts.google.com`
- **Microsoft Entra ID** - `https://login.microsoftonline.com/{tenant-id}/v2.0`
- **Okta** - `https://dev-123456.okta.com/oauth2/default`
- **Auth0** - `https://your-domain.auth0.com`
- **OneLogin** - `https://your-subdomain.onelogin.com/oidc/2`

### Self-Hosted
- **Authentik** - `https://auth.company.com/application/o/tailsentry/`
- **Keycloak** - `https://auth.company.com/realms/master`
- **FusionAuth** - `https://auth.company.com`
- **Dex** - `https://dex.company.com`
- **Zitadel** - `https://zitadel.company.com`

## 📚 Provider-Specific Guides

### 🔵 Google Workspace

1. **Create OAuth Application**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to **APIs & Services** → **Credentials**
   - Click **"Create Credentials"** → **"OAuth 2.0 Client IDs"**

2. **Configure Application**:
   ```
   Application Type: Web application
   Name: TailSentry SSO
   Authorized redirect URIs: [Copy from TailSentry]
   ```

3. **TailSentry Configuration**:
   ```
   Provider Name: Google Workspace
   Issuer URL: https://accounts.google.com
   Client ID: [From Google Console]
   Client Secret: [From Google Console]
   Scopes: openid email profile
   ```

### 🟢 Authentik

1. **Create Provider**:
   - Go to **Applications** → **Providers**
   - Click **"Create"** → **"OAuth2/OpenID Provider"**

2. **Provider Settings**:
   ```
   Name: TailSentry
   Authorization flow: default-authentication-flow
   Client type: Confidential
   Client ID: [Generate or custom]
   Client Secret: [Generate]
   Redirect URIs: [Copy from TailSentry]
   Signing Key: [Select certificate]
   ```

3. **TailSentry Configuration**:
   ```
   Provider Name: Authentik
   Issuer URL: https://auth.company.com/application/o/tailsentry/
   Client ID: [From Authentik]
   Client Secret: [From Authentik]
   Group Claim: groups
   ```

### 🔴 Keycloak

1. **Create Client**:
   - Go to **Clients** → **Create Client**
   - Client type: **OpenID Connect**
   - Client ID: `tailsentry`

2. **Client Settings**:
   ```
   Client authentication: ON
   Authorization: OFF
   Standard flow: ON
   Direct access grants: OFF
   Valid redirect URIs: [Copy from TailSentry]
   Web origins: https://tailsentry.company.com
   ```

3. **TailSentry Configuration**:
   ```
   Provider Name: Keycloak
   Issuer URL: https://auth.company.com/realms/master
   Client ID: tailsentry
   Client Secret: [From Credentials tab]
   Group Claim: realm_access.roles
   ```

### 🟠 Okta

1. **Create Application**:
   - Go to **Applications** → **Create App Integration**
   - Sign-in method: **OIDC - OpenID Connect**
   - Application type: **Web Application**

2. **Application Settings**:
   ```
   App integration name: TailSentry
   Grant type: Authorization Code
   Sign-in redirect URIs: [Copy from TailSentry]
   Sign-out redirect URIs: https://tailsentry.company.com/logout
   Controlled access: [Configure as needed]
   ```

3. **TailSentry Configuration**:
   ```
   Provider Name: Okta
   Issuer URL: https://dev-123456.okta.com/oauth2/default
   Client ID: [From Okta]
   Client Secret: [From Okta]
   Group Claim: groups
   ```

## ⚙️ Advanced Configuration

### Response Types
- **`code`** (Recommended): Authorization code flow
- **`token`**: Implicit flow (less secure)
- **`id_token`**: ID token only
- **`code token`**: Hybrid flow
- **`code id_token`**: Hybrid flow with ID token

### Additional Parameters
- **Prompt**: Force user interaction (`login`, `consent`, `none`)
- **Login Hint**: Domain hint for faster login (`@company.com`)
- **Scopes**: Additional OAuth scopes beyond `openid email profile`

### Enterprise Features
- **JWKS URI**: For token signature verification
- **Group Claims**: Map IdP groups to TailSentry roles
- **Logo URL**: Custom branding for login buttons

## 👥 Role Mapping

### Configuring Group Claims

1. **Set Group Claim Field**:
   ```
   Examples:
   - Google: groups
   - Authentik: groups
   - Keycloak: realm_access.roles
   - Okta: groups
   - Auth0: https://company.com/roles
   ```

2. **Configure Role Mappings** (JSON format):
   ```json
   {
     "tailsentry_admins": "admin",
     "tailsentry_users": "user",
     "tailsentry_readonly": "readonly",
     "it_team": "admin",
     "employees": "user"
   }
   ```

### Role Hierarchy
- **`admin`**: Full administrative access
- **`user`**: Standard user access
- **`readonly`**: Read-only access to dashboard

### Default Behavior
- Users without mapped groups get **`user`** role by default
- First admin login creates an admin user automatically

## 🔧 Troubleshooting

### Common Issues

#### 1. Discovery Failed
```bash
Error: Discovery failed: HTTP 404
```
**Solutions**:
- Verify issuer URL is correct
- Check if provider supports OIDC discovery
- Use manual endpoint configuration
- Ensure `.well-known/openid-configuration` is accessible

#### 2. Invalid Redirect URI
```bash
Error: redirect_uri_mismatch
```
**Solutions**:
- Copy exact redirect URI from TailSentry
- Ensure no trailing slashes or extra characters
- Check protocol matches (http vs https)
- Verify domain and port are correct

#### 3. Token Validation Failed
```bash
Error: Invalid token signature
```
**Solutions**:
- Verify client ID and secret are correct
- Check JWKS URI configuration
- Ensure issuer URL matches token issuer
- Validate scopes include `openid`

#### 4. Role Mapping Not Working
```bash
User has no role assigned
```
**Solutions**:
- Verify group claim field name
- Check user has groups in IdP
- Validate JSON syntax in role mappings
- Test with default user role

### Debug Mode

Enable debug logging by setting:
```bash
export LOG_LEVEL=DEBUG
```

### Testing Configuration

1. **Test Discovery**:
   ```bash
   curl https://your-issuer/.well-known/openid-configuration
   ```

2. **Validate Redirect URI**:
   - Use provider's OAuth testing tools
   - Check TailSentry logs for callback errors

3. **Verify Token Claims**:
   - Use JWT decoder tools
   - Check group/role claims are present

## 📞 Support

### Documentation
- [OIDC Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)

### Provider Documentation
- [Google OIDC](https://developers.google.com/identity/protocols/oauth2/openid-connect)
- [Microsoft Entra](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-protocols-oidc)
- [Okta OIDC](https://developer.okta.com/docs/reference/api/oidc/)
- [Auth0 OIDC](https://auth0.com/docs/protocols/openid-connect-protocol)
- [Authentik OIDC](https://docs.goauthentik.io/providers/oauth2/)
- [Keycloak OIDC](https://www.keycloak.org/docs/latest/server_admin/#_oidc)

### Getting Help
1. Check TailSentry logs in `/logs/tailsentry.log`
2. Verify provider configuration matches documentation
3. Test with minimal scopes first (`openid email`)
4. Use provider's testing tools when available

---

🎉 **Congratulations!** You now have enterprise-grade SSO configured for TailSentry. Users can sign in with their corporate credentials while maintaining proper role-based access control.
