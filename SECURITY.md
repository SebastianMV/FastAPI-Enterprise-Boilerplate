# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **DO NOT** create a public GitHub issue for security vulnerabilities
2. Email: <security@kairos.cl>
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Response Time:** We aim to respond within 48 hours
- **Updates:** We'll keep you informed of progress
- **Credit:** With your permission, we'll credit you in security advisories

### Scope

This policy applies to:

- The boilerplate code itself
- Default configurations
- Dependencies specified in requirements

### Out of Scope

- Vulnerabilities in user-modified code
- Issues from using outdated versions
- Deployment configuration errors

## Security Best Practices

When using this boilerplate, ensure you:

1. **Change default secrets** - Never use default JWT keys in production
2. **Use HTTPS** - Always deploy behind TLS/SSL
3. **Keep dependencies updated** - Run `pip install --upgrade` regularly
4. **Enable rate limiting** - Configure Redis for production rate limits
5. **Review CORS settings** - Restrict allowed origins in production
6. **Use strong passwords** - Enforce password policies
7. **Enable logging** - Monitor for suspicious activity
8. **Regular backups** - Backup database regularly

## Security Features

This boilerplate includes:

- ✅ JWT authentication with refresh tokens
- ✅ Password hashing with bcrypt (12 rounds)
- ✅ Rate limiting (configurable)
- ✅ CORS protection
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS protection (Pydantic validation)
- ✅ CSRF protection (SameSite cookies)
- ✅ Secure headers middleware
- ✅ Input validation (Pydantic)
- ✅ Multi-tenant data isolation (RLS)
