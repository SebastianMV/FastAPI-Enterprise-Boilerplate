# Email Templates System

This document describes the email templating system with internationalization (i18n) support.

## Overview

The email system provides:

- **Jinja2 Templates**: HTML and plain text email templates
- **i18n Support**: Multi-language emails (English, Spanish, Portuguese)
- **Pluggable Backends**: Console (dev), SMTP, SendGrid, AWS SES, Mailgun
- **Template Types**: 9 pre-built email templates for common use cases

## Quick Start

```python
from app.infrastructure.email import EmailService, EmailTemplateEngine
from app.infrastructure.i18n import get_i18n

# Initialize
i18n = get_i18n()
template_engine = EmailTemplateEngine(i18n)
email_service = EmailService(template_engine)

# Send verification email
await email_service.send_verification_email(
    to_email="user@example.com",
    user_name="John Doe",
    verification_link="https://app.example.com/verify?token=abc123",
    locale="en"
)
```

## Configuration

### Environment Variables

```bash
# Email Backend (console, smtp, sendgrid, aws_ses, mailgun)
EMAIL_BACKEND=smtp
EMAIL_FROM=noreply@example.com
EMAIL_FROM_NAME="My Application"
EMAIL_SUPPORT=support@example.com

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true
SMTP_SSL=false

# SendGrid Configuration
SENDGRID_API_KEY=SG.xxxxx

# AWS SES Configuration
SES_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Mailgun Configuration
MAILGUN_API_KEY=key-xxxxx
MAILGUN_DOMAIN=mg.example.com
```

## Available Templates

### 1. Registration Email

Sent when a new user registers.

```python
await email_service.send_registration_email(
    to_email="user@example.com",
    user_name="John Doe",
    verification_link="https://app.com/verify?token=xyz",
    locale="en"  # or "es", "pt"
)
```

### 2. Email Verification

Request to verify email address.

```python
await email_service.send_verification_email(
    to_email="user@example.com",
    user_name="John Doe",
    verification_link="https://app.com/verify?token=xyz",
    expires_hours=24,
    locale="es"
)
```

### 3. Password Reset

Password reset request with secure link.

```python
await email_service.send_password_reset_email(
    to_email="user@example.com",
    user_name="John Doe",
    reset_link="https://app.com/reset?token=xyz",
    expires_hours=1,
    locale="pt"
)
```

### 4. Welcome Email

Sent after email verification.

```python
await email_service.send_welcome_email(
    to_email="user@example.com",
    user_name="John Doe",
    login_url="https://app.com/login",
    locale="en"
)
```

### 5. Password Changed

Security notification when password is changed.

```python
await email_service.send_password_changed_email(
    to_email="user@example.com",
    user_name="John Doe",
    ip_address="192.168.1.1",
    device="Chrome on Windows",
    secure_account_url="https://app.com/security",
    locale="en"
)
```

### 6. Login from New Device

Security alert for new device login.

```python
await email_service.send_login_new_device_email(
    to_email="user@example.com",
    user_name="John Doe",
    device="iPhone 15",
    location="New York, US",
    ip_address="192.168.1.1",
    secure_account_url="https://app.com/security",
    locale="en"
)
```

### 7. Account Locked

Notification when account is locked.

```python
await email_service.send_account_locked_email(
    to_email="user@example.com",
    user_name="John Doe",
    reason="Too many failed login attempts",
    unlock_url="https://app.com/unlock?token=xyz",
    locale="en"
)
```

### 8. MFA Enabled

Confirmation when 2FA is enabled.

```python
await email_service.send_mfa_enabled_email(
    to_email="user@example.com",
    user_name="John Doe",
    locale="en"
)
```

### 9. Tenant Invitation

Invite users to join an organization.

```python
await email_service.send_tenant_invitation_email(
    to_email="user@example.com",
    user_name="John Doe",
    tenant_name="Acme Corp",
    inviter_name="Jane Smith",
    role="Developer",
    invitation_link="https://app.com/invite?token=xyz",
    locale="en"
)
```

## Internationalization (i18n)

### Supported Languages

| Code | Language   | Locale File |
|------|------------|-------------|
| en   | English    | en.json     |
| es   | Spanish    | es.json     |
| pt   | Portuguese | pt.json     |

### Translation Keys Structure

All email translations follow this structure in locale files:

```json
{
  "email": {
    "common": {
      "sent_by": "This email was sent by {app_name}",
      "questions": "Questions? Contact us at",
      "all_rights_reserved": "All rights reserved."
    },
    "registration": {
      "subject": "Welcome to {app_name} - Account Created",
      "preheader": "Your {app_name} account has been created successfully",
      "title": "Account Created Successfully",
      "greeting": "Hello {name},",
      "body": "Thank you for signing up...",
      "verify_button": "Verify Email",
      ...
    },
    "email_verification": { ... },
    "password_reset": { ... },
    "welcome": { ... },
    "password_changed": { ... },
    "login_new_device": { ... },
    "account_locked": { ... },
    "mfa_enabled": { ... },
    "tenant_invitation": { ... }
  }
}
```

### Adding New Languages

1. Create a new locale file: `infrastructure/i18n/locales/fr.json`
2. Add all email translations following the same structure
3. Add the locale to `EmailTemplateEngine.SUPPORTED_LOCALES`

```python
class EmailTemplateEngine:
    SUPPORTED_LOCALES = ["en", "es", "pt", "fr"]  # Add new locale
```

## Custom Templates

### Creating a New Template

1. Create template files in `infrastructure/email/templates/your_template/`:

**html.jinja2:**

```jinja2
{% extends "base.html.jinja2" %}

{% block preheader %}{{ t('email.your_template.preheader') }}{% endblock %}

{% block content %}
<tr>
    <td style="padding: 0 24px;">
        <h1>{{ t('email.your_template.title') }}</h1>
        <p>{{ t('email.your_template.greeting', name=name) }}</p>
        <p>{{ t('email.your_template.body') }}</p>
    </td>
</tr>
{% endblock %}

{% block cta %}
<tr>
    <td style="padding: 24px;">
        <a href="{{ action_url }}" class="button">
            {{ t('email.your_template.button') }}
        </a>
    </td>
</tr>
{% endblock %}
```

**text.jinja2:**

```jinja2
{% extends "base.text.jinja2" %}

{% block content %}
{{ t('email.your_template.title') }}
{{ '=' * t('email.your_template.title')|length }}

{{ t('email.your_template.greeting', name=name) }}

{{ t('email.your_template.body') }}

{{ t('email.your_template.button') }}: {{ action_url }}
{% endblock %}
```

1. Add template type to enum:

```python
class EmailTemplateType(str, Enum):
    YOUR_TEMPLATE = "your_template"
```

1. Add translation keys to all locale files.

1. Add convenience method to EmailService:

```python
async def send_your_template_email(
    self,
    to_email: str,
    user_name: str,
    action_url: str,
    locale: str = "en"
) -> bool:
    template = self.template_engine.render(
        EmailTemplateType.YOUR_TEMPLATE,
        locale=locale,
        context={
            "name": user_name,
            "action_url": action_url,
        }
    )
    return await self.send_email(to_email, template)
```

## Template Structure

### Base HTML Template

The base HTML template (`base.html.jinja2`) provides:

- Responsive email layout
- Email client compatibility
- Consistent styling
- Dark mode support (where supported)

### Blocks Available

| Block | Purpose |
| ------- | --------- |
| `preheader` | Preview text in email clients |
| `content` | Main email content |
| `cta` | Call-to-action button |
| `footer_extra` | Additional footer content |

## Email Backends

### Console Backend (Development)

Prints emails to console instead of sending. Perfect for development.

```bash
EMAIL_BACKEND=console
```

### SMTP Backend

Standard SMTP server connection.

```bash
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true
```

### SendGrid Backend

Uses SendGrid API for sending.

```bash
EMAIL_BACKEND=sendgrid
SENDGRID_API_KEY=SG.xxxxx
```

### AWS SES Backend

Uses Amazon Simple Email Service.

```bash
EMAIL_BACKEND=aws_ses
SES_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

### Mailgun Backend

Uses Mailgun API for sending.

```bash
EMAIL_BACKEND=mailgun
MAILGUN_API_KEY=key-xxxxx
MAILGUN_DOMAIN=mg.example.com
```

## Testing

### Unit Testing

```python
import pytest
from app.infrastructure.email import EmailTemplateEngine
from app.infrastructure.i18n import get_i18n

@pytest.fixture
def template_engine():
    i18n = get_i18n()
    return EmailTemplateEngine(i18n)

def test_render_registration_email(template_engine):
    template = template_engine.render(
        EmailTemplateType.REGISTRATION,
        locale="en",
        context={
            "name": "Test User",
            "email": "test@example.com",
            "verification_link": "https://example.com/verify",
            "app_name": "Test App",
            "support_email": "support@example.com",
        }
    )
    
    assert template.subject == "Welcome to Test App - Account Created"
    assert "Test User" in template.html_body
    assert "verify" in template.html_body.lower()

def test_render_all_locales(template_engine):
    for locale in ["en", "es", "pt"]:
        template = template_engine.render(
            EmailTemplateType.EMAIL_VERIFICATION,
            locale=locale,
            context={
                "name": "User",
                "verification_link": "https://example.com/verify",
                "hours": 24,
                "app_name": "App",
                "support_email": "support@example.com",
            }
        )
        assert template.locale == locale
        assert template.html_body
        assert template.text_body
```

### Integration Testing

```python
import pytest
from app.infrastructure.email import EmailService, EmailTemplateEngine
from app.infrastructure.i18n import get_i18n

@pytest.fixture
async def email_service():
    i18n = get_i18n()
    template_engine = EmailTemplateEngine(i18n)
    return EmailService(template_engine, backend="console")

@pytest.mark.asyncio
async def test_send_verification_email(email_service, capsys):
    result = await email_service.send_verification_email(
        to_email="test@example.com",
        user_name="Test User",
        verification_link="https://example.com/verify",
        locale="en"
    )
    
    assert result is True
    captured = capsys.readouterr()
    assert "test@example.com" in captured.out
    assert "Verify" in captured.out
```

## Best Practices

1. **Always provide fallback locale**: If a translation is missing, the system falls back to English.

2. **Use consistent variable names**: Template variables should be clear and consistent across templates.

3. **Test all locales**: Ensure translations are complete for all supported languages.

4. **Preview emails**: Use the console backend during development to preview email content.

5. **Handle errors gracefully**: Always catch and log email sending errors.

```python
try:
    await email_service.send_verification_email(...)
except Exception as e:
    logger.error(f"Failed to send verification email: {e}")
    # Continue with user registration even if email fails
```

## Troubleshooting

### Common Issues

**Email not sending:**

- Check EMAIL_BACKEND is set correctly
- Verify SMTP credentials
- Check firewall/network settings

**Missing translations:**

- Verify translation keys exist in locale files
- Check locale code is correct (en, es, pt)
- Falls back to English if translation missing

**Template not rendering:**

- Check template file exists
- Verify Jinja2 syntax is correct
- Check all required variables are provided

### Debug Mode

Enable debug logging to see email content:

```python
import logging
logging.getLogger("app.infrastructure.email").setLevel(logging.DEBUG)
```
