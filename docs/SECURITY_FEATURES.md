# Security Features

This document describes the security features available in the FastAPI Enterprise Boilerplate.

## Table of Contents

1. [Account Lockout](#account-lockout)
2. [Session Management](#session-management)
3. [Email Verification](#email-verification)
4. [Multi-Factor Authentication (MFA)](#multi-factor-authentication)
5. [API Keys](#api-keys)

---

## Account Lockout

Protects against brute-force attacks by temporarily locking accounts after multiple failed login attempts.

### Configuration

Configure in `.env` or environment variables:

```env
# Enable/disable account lockout (default: true)
ACCOUNT_LOCKOUT_ENABLED=true

# Number of failed attempts before lockout (default: 5, range: 3-10)
ACCOUNT_LOCKOUT_THRESHOLD=5

# Lockout duration in minutes (default: 30, range: 5-1440)
ACCOUNT_LOCKOUT_DURATION_MINUTES=30
```

### Behavior

1. **Failed Login Tracking**: Each failed login attempt increments `failed_login_attempts`
2. **Automatic Lockout**: After `ACCOUNT_LOCKOUT_THRESHOLD` failures, the account is locked
3. **Lock Duration**: Account remains locked for `ACCOUNT_LOCKOUT_DURATION_MINUTES` minutes
4. **Automatic Unlock**: Lock expires automatically after the duration
5. **Reset on Success**: Successful login resets the failed attempts counter

### API Responses

When an account is locked:

```json
{
  "status_code": 423,
  "detail": {
    "code": "ACCOUNT_LOCKED",
    "message": "Account is locked. Try again in 25 minute(s)."
  }
}
```

### Admin Unlock

Administrators can manually unlock accounts:

```python
# In code
user.unlock()
await user_repository.update(user)
```

---

## Session Management

Track and manage active login sessions across devices.

### Features

- **View Active Sessions**: See all devices where you're logged in
- **Session Details**: Device name, browser, OS, IP address, location, last activity
- **Revoke Sessions**: Log out from specific devices or all other devices
- **Current Session Badge**: Clearly identifies which session you're currently using

### API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/api/v1/sessions` | List all active sessions |
| DELETE | `/api/v1/sessions/{id}` | Revoke a specific session |
| DELETE | `/api/v1/sessions` | Revoke all sessions except current |

### Example Response

```json
{
  "sessions": [
    {
      "id": "uuid-here",
      "device_name": "Chrome on Windows",
      "device_type": "desktop",
      "browser": "Chrome",
      "os": "Windows",
      "ip_address": "192.168.1.100",
      "location": "Santiago, Chile",
      "last_activity": "2026-01-12T10:30:00Z",
      "is_current": true,
      "created_at": "2026-01-10T08:00:00Z"
    }
  ],
  "total": 1
}
```

### UI Access

Navigate to **Settings > Security > Active Sessions** to manage sessions.

---

## Email Verification

Ensure users have valid email addresses.

### Configuration

```env
# Require email verification for new users (default: true)
EMAIL_VERIFICATION_REQUIRED=true

# Token expiration in hours (default: 24, range: 1-72)
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24
```

### Flow

1. **Registration**: New users receive verification email automatically
2. **Verification Link**: Email contains a unique token link
3. **Verification Page**: User clicks link and is verified
4. **Resend Option**: Users can request new verification email

### API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/api/v1/auth/send-verification` | Send/resend verification email |
| POST | `/api/v1/auth/verify-email?token=xxx` | Verify email with token |
| GET | `/api/v1/auth/verification-status` | Check verification status |

### UI Components

- **Banner**: Yellow warning banner appears when email is not verified
- **Resend Button**: Users can resend verification from the banner
- **Verification Page**: `/verify-email?token=xxx` handles the verification

### Behavior Options

When `EMAIL_VERIFICATION_REQUIRED=true`:

- Users can still log in without verification
- Some features may be restricted (configurable)
- Banner reminds user to verify

When `EMAIL_VERIFICATION_REQUIRED=false`:

- Users are marked as verified by default
- No verification emails are sent

---

## Multi-Factor Authentication

See [MFA documentation](./GETTING_STARTED.md#mfa-setup) for TOTP-based two-factor authentication.

---

## API Keys

See [API Keys documentation](./GETTING_STARTED.md#api-keys) for machine-to-machine authentication.

---

## Security Best Practices

### Recommended Settings for Production

```env
# Account Lockout
ACCOUNT_LOCKOUT_ENABLED=true
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_DURATION_MINUTES=30

# Email Verification
EMAIL_VERIFICATION_REQUIRED=true
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24

# JWT Tokens
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
```

### Security Checklist

- [ ] Enable account lockout in production
- [ ] Require email verification
- [ ] Set strong JWT secret key (min 32 characters)
- [ ] Enable rate limiting
- [ ] Use HTTPS in production
- [ ] Configure proper CORS origins
- [ ] Review and enable MFA for admin accounts
