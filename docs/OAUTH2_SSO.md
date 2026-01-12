# OAuth2 & SSO Authentication

This document describes the OAuth2 and Single Sign-On (SSO) authentication features available in the FastAPI Enterprise Boilerplate.

## Overview

The boilerplate supports multiple OAuth2 providers out of the box:

| Provider | Status | Features |
| --- | --- | --- |
| Google | ✅ Ready | Email, profile, OIDC |
| GitHub | ✅ Ready | Email, profile, organizations |
| Microsoft | ✅ Ready | Azure AD, multi-tenant |
| Apple | 🔜 Planned | OIDC with SIWA |
| Facebook | 🔜 Planned | Email, profile |
| SAML 2.0 | 🔜 Planned | Enterprise SSO |

## Quick Start

### 1. Configure OAuth Providers

Add credentials to your `.env` file:

```bash
# Base URL for OAuth callbacks
APP_BASE_URL=http://localhost:8000

# Google OAuth
OAUTH_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
OAUTH_GOOGLE_CLIENT_SECRET=your-google-secret

# GitHub OAuth
OAUTH_GITHUB_CLIENT_ID=your-github-client-id
OAUTH_GITHUB_CLIENT_SECRET=your-github-secret

# Microsoft/Azure AD OAuth
OAUTH_MICROSOFT_CLIENT_ID=your-microsoft-client-id
OAUTH_MICROSOFT_CLIENT_SECRET=your-microsoft-secret
OAUTH_MICROSOFT_TENANT_ID=common  # or specific tenant ID
```

### 2. Run Database Migration

```bash
alembic upgrade head
```

### 3. Test OAuth Flow

```bash
# Get available providers
curl http://localhost:8000/api/v1/auth/oauth/providers

# Start OAuth flow
curl http://localhost:8000/api/v1/auth/oauth/google/authorize
```

## API Reference

### Available Endpoints

#### List Available Providers

```http
GET /api/v1/auth/oauth/providers
```

Returns list of configured OAuth providers and their availability.

#### Start OAuth Flow

```http
GET /api/v1/auth/oauth/{provider}/authorize
```

Parameters:

| Name | Type | Description |
| --- | --- | --- |
| provider | path | Provider name (google, github, microsoft) |
| redirect_uri | query | Custom redirect URI (optional) |
| scope | query | Additional scopes (space-separated) |

Response:

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random-state-token"
}
```

#### Direct Redirect (Browser Flow)

```http
GET /api/v1/auth/oauth/{provider}/authorize/redirect
```

Redirects user directly to the OAuth provider.

#### OAuth Callback

```http
GET /api/v1/auth/oauth/{provider}/callback
```

Parameters:

| Name | Type | Description |
| --- | --- | --- |
| code | query | Authorization code from provider |
| state | query | State for CSRF protection |

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_new_user": true
}
```

### Account Linking

#### Link OAuth Account to Existing User

```http
POST /api/v1/auth/oauth/{provider}/link
Authorization: Bearer {access_token}
```

#### List User's OAuth Connections

```http
GET /api/v1/auth/oauth/connections
Authorization: Bearer {access_token}
```

#### Unlink OAuth Account

```http
DELETE /api/v1/auth/oauth/connections/{connection_id}
Authorization: Bearer {access_token}
```

### SSO Configuration (Admin)

#### List SSO Configurations

```http
GET /api/v1/auth/oauth/sso/configs
Authorization: Bearer {admin_token}
```

#### Create SSO Configuration

```http
POST /api/v1/auth/oauth/sso/configs
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "provider": "google",
  "name": "Corporate Google SSO",
  "client_id": "...",
  "client_secret": "...",
  "scopes": ["openid", "email", "profile"],
  "auto_create_users": true,
  "allowed_domains": ["company.com"]
}
```

## Frontend Integration

### React Example

```tsx
import { useState } from 'react';

const OAuthButtons = () => {
  const [loading, setLoading] = useState(false);

  const handleOAuth = async (provider: string) => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/v1/auth/oauth/${provider}/authorize`
      );
      const data = await response.json();
      
      // Redirect to OAuth provider
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error('OAuth error:', error);
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={() => handleOAuth('google')}
        className="flex items-center gap-2 px-4 py-2 bg-white border rounded"
        disabled={loading}
      >
        <GoogleIcon />
        Continue with Google
      </button>
      <button
        onClick={() => handleOAuth('github')}
        className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded"
        disabled={loading}
      >
        <GitHubIcon />
        Continue with GitHub
      </button>
    </div>
  );
};
```

### Callback Handler

```tsx
// pages/auth/callback.tsx
import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

const OAuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  useEffect(() => {
    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');
    const error = searchParams.get('error');

    if (error) {
      console.error('OAuth error:', error);
      navigate('/login?error=' + error);
      return;
    }

    if (accessToken && refreshToken) {
      setAuth({ accessToken, refreshToken });
      navigate('/dashboard');
    }
  }, [searchParams]);

  return <div>Processing login...</div>;
};
```

## Provider Setup Guides

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Go to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth Client ID**
5. Select **Web application**
6. Add authorized redirect URI: `http://localhost:8000/api/v1/auth/oauth/google/callback`
7. Copy Client ID and Client Secret

### GitHub OAuth

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in:
   - Application name: Your App Name
   - Homepage URL: `http://localhost:8000`
   - Callback URL: `http://localhost:8000/api/v1/auth/oauth/github/callback`
4. Copy Client ID and generate a Client Secret

### Microsoft/Azure AD

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Select account types (single or multi-tenant)
5. Add redirect URI: `http://localhost:8000/api/v1/auth/oauth/microsoft/callback`
6. Go to **Certificates & secrets** > **New client secret**
7. Copy Application (client) ID and secret

## Security Considerations

### PKCE (Proof Key for Code Exchange)

All OAuth flows use PKCE for enhanced security. This prevents authorization code interception attacks.

### State Parameter

A cryptographically random state parameter is generated and verified to prevent CSRF attacks.

### Token Storage

- OAuth access tokens are stored encrypted in the database
- Tokens are automatically refreshed when expired
- Tokens can be revoked by unlinking the OAuth connection

### Domain Restrictions

SSO configurations can restrict which email domains are allowed:

```json
{
  "allowed_domains": ["company.com", "corp.company.com"]
}
```

## Troubleshooting

### "Invalid or expired OAuth state"

The OAuth flow took too long (>10 minutes) or the state was tampered with. Start the flow again.

### "Provider mismatch"

The callback was received from a different provider than expected. This could indicate a security issue.

### "This OAuth account is linked to another user"

The OAuth account is already linked to a different user. Unlink it from the other account first.

### "Cannot unlink primary OAuth account without setting a password"

Set a password before unlinking the only OAuth connection, or link another OAuth provider first.

## Advanced Configuration

### Custom OAuth Provider

Extend `OAuthProviderBase` to add custom providers:

```python
from app.infrastructure.auth.oauth_providers import OAuthProviderBase

class CustomOAuthProvider(OAuthProviderBase):
    name = "custom"
    authorization_url = "https://custom.example.com/oauth/authorize"
    token_url = "https://custom.example.com/oauth/token"
    userinfo_url = "https://custom.example.com/api/userinfo"
    default_scopes = ["openid", "profile", "email"]

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        # Implement user info fetching
        ...
```

### SAML 2.0 (Enterprise)

SAML support is planned for enterprise deployments. Contact support for early access.
