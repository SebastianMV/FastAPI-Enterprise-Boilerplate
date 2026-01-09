# API Reference

Complete API documentation with examples for the FastAPI Enterprise Boilerplate.

## Base URL

```text
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

## Authentication

All endpoints (except `/auth/login` and `/auth/register`) require authentication.

### JWT Bearer Token

Include the access token in the `Authorization` header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### API Key

For machine-to-machine communication, use the `X-API-Key` header:

```http
X-API-Key: bp_abc123def456...
```

---

## Endpoints

### Authentication

#### POST /auth/login

Authenticate user and get tokens.

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Admin123!@#"
  }'
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "admin@example.com",
    "first_name": "Admin",
    "last_name": "User",
    "is_superuser": true
  }
}
```

**Errors:**

| Status | Description         |
| ------ | ------------------- |
| 401    | Invalid credentials |
| 422    | Validation error    |

---

#### POST /auth/register

Register a new user account.

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "newuser@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "created_at": "2026-01-06T12:00:00Z"
}
```

---

#### POST /auth/refresh

Refresh access token using refresh token.

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

#### POST /auth/logout

Invalidate current tokens.

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**

```json
{
  "message": "Successfully logged out"
}
```

---

#### POST /auth/forgot-password 🆕

Request password reset email. Always returns success to prevent email enumeration.

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**Response (200 OK):**

```json
{
  "message": "If this email exists, a password reset link has been sent"
}
```

---

#### POST /auth/verify-reset-token 🆕

Verify if a password reset token is valid.

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-reset-token \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123def456..."
  }'
```

**Response (200 OK):**

```json
{
  "valid": true,
  "email": "user@example.com",
  "expires_in_minutes": 45
}
```

**Errors:**

| Status | Description |
| ------ | ----------- |
| 400 | Invalid or expired token |

---

#### POST /auth/reset-password 🆕

Reset password using valid token.

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123def456...",
    "new_password": "NewSecure123!"
  }'
```

**Response (200 OK):**

```json
{
  "message": "Password reset successfully"
}
```

**Errors:**

| Status | Description |
| ------ | ----------- |
| 400 | Invalid or expired token |
| 422 | Password too weak |

---

### Users

#### GET /users

List all users (requires `users:read` permission).

**Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/users?limit=10&skip=0" \
  -H "Authorization: Bearer <access_token>"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| skip | int | 0 | Number of records to skip |
| limit | int | 100 | Maximum records to return (max 1000) |
| is_active | bool | - | Filter by active status |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "admin@example.com",
      "first_name": "Admin",
      "last_name": "User",
      "is_active": true,
      "is_superuser": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 10
}
```

---

#### GET /users/{user_id}

Get user by ID (requires `users:read` permission).

**Request:**

```bash
curl -X GET http://localhost:8000/api/v1/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "first_name": "Admin",
  "last_name": "User",
  "is_active": true,
  "is_superuser": true,
  "roles": ["Administrator"],
  "created_at": "2026-01-01T00:00:00Z",
  "last_login": "2026-01-06T10:30:00Z"
}
```

---

#### POST /users

Create a new user (requires `users:create` permission).

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "first_name": "Jane",
    "last_name": "Smith",
    "role_ids": ["550e8400-e29b-41d4-a716-446655440010"]
  }'
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "email": "newuser@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "is_active": true,
  "created_at": "2026-01-06T12:00:00Z"
}
```

---

#### PATCH /users/{user_id}

Update user (requires `users:update` permission).

**Request:**

```bash
curl -X PATCH http://localhost:8000/api/v1/users/550e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Janet",
    "is_active": false
  }'
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "email": "newuser@example.com",
  "first_name": "Janet",
  "last_name": "Smith",
  "is_active": false,
  "updated_at": "2026-01-06T12:30:00Z"
}
```

---

#### DELETE /users/{user_id}

Delete user (requires `users:delete` permission). Uses soft delete.

**Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/users/550e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer <access_token>"
```

Response: 204 No Content

---

### Roles

#### GET /roles

List all roles (requires `roles:read` permission).

**Request:**

```bash
curl -X GET http://localhost:8000/api/v1/roles \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Administrator",
      "description": "Full system access",
      "permissions": ["*:*"],
      "is_system": true
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440011",
      "name": "Manager",
      "description": "Team management access",
      "permissions": ["users:read", "users:update", "reports:*"],
      "is_system": true
    }
  ],
  "total": 2
}
```

---

#### POST /roles

Create a new role (requires `roles:create` permission).

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/roles \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Support Agent",
    "description": "Customer support access",
    "permissions": ["tickets:read", "tickets:update", "users:read"]
  }'
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440020",
  "name": "Support Agent",
  "description": "Customer support access",
  "permissions": ["tickets:read", "tickets:update", "users:read"],
  "is_system": false,
  "created_at": "2026-01-06T12:00:00Z"
}
```

---

### Tenants

#### GET /tenants/current

Get current tenant information.

**Request:**

```bash
curl -X GET http://localhost:8000/api/v1/tenants/current \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440100",
  "name": "Acme Corporation",
  "slug": "acme",
  "plan": "professional",
  "is_active": true,
  "settings": {
    "theme": "light",
    "timezone": "America/Santiago",
    "locale": "es-CL"
  },
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

### API Keys

#### POST /api-keys

Generate a new API key (requires `apikeys:create` permission).

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD Integration",
    "scopes": ["users:read", "reports:read"],
    "expires_in_days": 365
  }'
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440200",
  "name": "CI/CD Integration",
  "key": "bp_abc123def456ghi789jkl012mno345pqr678",
  "prefix": "bp_abc12",
  "scopes": ["users:read", "reports:read"],
  "expires_at": "2027-01-06T12:00:00Z",
  "created_at": "2026-01-06T12:00:00Z"
}
```

> ⚠️ **Important:** The `key` field is only shown once at creation. Store it securely!

---

#### GET /api-keys

List all API keys (requires `apikeys:read` permission).

**Request:**

```bash
curl -X GET http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440200",
      "name": "CI/CD Integration",
      "prefix": "bp_abc12",
      "scopes": ["users:read", "reports:read"],
      "is_active": true,
      "last_used_at": "2026-01-06T10:00:00Z",
      "expires_at": "2027-01-06T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### DELETE /api-keys/{key_id}

Revoke an API key (requires `apikeys:delete` permission).

**Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/api-keys/550e8400-e29b-41d4-a716-446655440200 \
  -H "Authorization: Bearer <access_token>"
```

Response: 204 No Content

---

### Health

#### GET /health

Check API health status (no authentication required).

**Request:**

```bash
curl -X GET http://localhost:8000/api/v1/health
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-06T12:00:00Z",
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "field": "field_name"
  }
}
```

### Common Error Codes

| HTTP Status | Code | Description |
| ----------- | ---- | ----------- |
| 400 | `VALIDATION_ERROR` | Request validation failed |
| 401 | `AUTHENTICATION_ERROR` | Invalid or missing credentials |
| 403 | `PERMISSION_DENIED` | User lacks required permission |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource already exists |
| 422 | `UNPROCESSABLE_ENTITY` | Request body validation failed |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |

---

## Rate Limiting

API requests are rate-limited per user/IP:

- **Default limit:** 100 requests per minute
- **Burst limit:** 10 requests per second

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704542400
```

When rate limited, you'll receive:

```json
{
  "detail": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Try again in 45 seconds.",
    "retry_after": 45
  }
}
```

---

## Pagination

List endpoints support pagination with these parameters:

| Parameter | Type | Default | Max  | Description      |
| --------- | ---- | ------- | ---- | ---------------- |
| skip      | int  | 0       | -    | Records to skip  |
| limit     | int  | 100     | 1000 | Records per page |

Response includes pagination metadata:

```json
{
  "items": [...],
  "total": 150,
  "skip": 0,
  "limit": 100,
  "has_more": true
}
```

---

## Multi-Tenant Isolation

All data is automatically isolated by tenant. The tenant is determined from:

1. JWT token `tenant_id` claim
2. `X-Tenant-ID` header (for superusers)
3. User's default tenant

You cannot access data from other tenants.

---

## SDK Examples

### Python

```python
import httpx

class BoilerplateClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def get_users(self, limit: int = 100) -> dict:
        response = httpx.get(
            f"{self.base_url}/users",
            params={"limit": limit},
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

# Usage
client = BoilerplateClient(
    "http://localhost:8000/api/v1",
    "bp_abc123def456..."
)
users = client.get_users(limit=10)
```

### JavaScript/TypeScript

```typescript
class BoilerplateClient {
  constructor(
    private baseUrl: string,
    private apiKey: string
  ) {}

  async getUsers(limit = 100): Promise<UserList> {
    const response = await fetch(
      `${this.baseUrl}/users?limit=${limit}`,
      {
        headers: {
          'X-API-Key': this.apiKey,
        },
      }
    );
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
  }
}

// Usage
const client = new BoilerplateClient(
  'http://localhost:8000/api/v1',
  'bp_abc123def456...'
);
const users = await client.getUsers(10);
```

---

## OpenAPI Specification

Full OpenAPI 3.0 specification is available at:

- **Swagger UI:** <http://localhost:8000/docs>
- **ReDoc:** <http://localhost:8000/redoc>
- **OpenAPI JSON:** <http://localhost:8000/openapi.json>
