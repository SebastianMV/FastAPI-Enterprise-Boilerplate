# Bulk Operations API

This document describes the Bulk Operations API, which allows administrators to perform efficient batch operations on multiple entities at once.

## Overview

The Bulk Operations API provides endpoints for:

- **Bulk User Creation**: Create multiple users in a single request
- **Bulk User Updates**: Update multiple users simultaneously
- **Bulk User Deletion**: Delete or deactivate multiple users
- **Bulk Status Changes**: Activate/deactivate users in bulk
- **Bulk Role Assignment**: Assign or remove roles from multiple users
- **Data Validation**: Validate bulk data before executing operations

All bulk endpoints require **superuser privileges** (except validation endpoint which requires any authenticated user).

## Endpoints

### POST /api/v1/bulk/users/create

Create multiple users in a single request.

**Request Body:**
```json
{
  "users": [
    {
      "email": "user1@example.com",
      "password": "SecurePass123!",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true,
      "roles": ["uuid-of-role"]
    },
    {
      "email": "user2@example.com",
      "password": "SecurePass456!",
      "first_name": "Jane",
      "last_name": "Smith"
    }
  ],
  "skip_duplicates": true,
  "send_welcome_email": false
}
```

**Options:**
- `skip_duplicates` (default: `false`): Skip users with duplicate emails instead of failing
- `send_welcome_email` (default: `false`): Send welcome email to created users

**Response:**
```json
{
  "operation": "create",
  "entity_type": "users",
  "total_requested": 2,
  "successful": 2,
  "failed": 0,
  "skipped": 0,
  "results": [
    {
      "index": 0,
      "success": true,
      "entity_id": "created-user-uuid",
      "message": "User created successfully"
    },
    {
      "index": 1,
      "success": true,
      "entity_id": "created-user-uuid-2",
      "message": "User created successfully"
    }
  ]
}
```

### POST /api/v1/bulk/users/update

Update multiple users in a single request.

**Request Body:**
```json
{
  "users": [
    {
      "id": "user-uuid-1",
      "first_name": "Updated",
      "is_active": false
    },
    {
      "id": "user-uuid-2",
      "last_name": "NewLastName"
    }
  ],
  "skip_not_found": true
}
```

**Options:**
- `skip_not_found` (default: `false`): Skip non-existent users instead of failing

**Response:**
```json
{
  "operation": "update",
  "entity_type": "users",
  "total_requested": 2,
  "successful": 2,
  "failed": 0,
  "skipped": 0,
  "results": [...]
}
```

### POST /api/v1/bulk/users/delete

Delete or deactivate multiple users.

**Request Body:**
```json
{
  "user_ids": [
    "user-uuid-1",
    "user-uuid-2",
    "user-uuid-3"
  ],
  "hard_delete": false,
  "skip_not_found": true
}
```

**Options:**
- `hard_delete` (default: `false`): Permanently delete users instead of soft-delete
- `skip_not_found` (default: `false`): Skip non-existent users

**Note:** You cannot delete yourself in a bulk operation.

### POST /api/v1/bulk/users/status

Quick activate/deactivate multiple users.

**Request Body:**
```json
{
  "user_ids": [
    "user-uuid-1",
    "user-uuid-2"
  ],
  "is_active": false
}
```

### POST /api/v1/bulk/users/roles

Assign or remove roles from multiple users.

**Request Body:**
```json
{
  "user_ids": [
    "user-uuid-1",
    "user-uuid-2"
  ],
  "role_ids": [
    "role-uuid-1"
  ],
  "operation": "assign"
}
```

**Options:**
- `operation`: Either `"assign"` to add roles or `"remove"` to remove roles

### POST /api/v1/bulk/validate

Validate bulk operation data before executing.

**Request Body:**
```json
{
  "entity_type": "users",
  "operation": "create",
  "data": [
    {
      "email": "valid@example.com",
      "password": "SecurePass123!",
      "first_name": "Test",
      "last_name": "User"
    },
    {
      "email": "invalid-email",
      "password": "short"
    }
  ]
}
```

**Response:**
```json
{
  "valid": false,
  "total": 2,
  "valid_count": 1,
  "invalid_count": 1,
  "errors": [
    {
      "index": 1,
      "errors": [
        "Invalid email format",
        "Password must be at least 8 characters"
      ]
    }
  ]
}
```

## Limits

- Maximum **100 items** per bulk request
- Operations are performed sequentially to maintain data integrity
- All operations are audited

## Error Handling

The API uses a partial success model:
- Each item's result is reported individually
- The overall response includes counts of successful, failed, and skipped items
- Individual failures don't stop the entire operation

## Audit Logging

All bulk operations are logged to the audit trail with:
- Operation type (BULK_CREATE, BULK_UPDATE, BULK_DELETE)
- Number of items affected
- User who performed the operation
- Timestamp

## Best Practices

1. **Validate First**: Use the `/bulk/validate` endpoint before executing large operations
2. **Use skip_duplicates**: When importing data, enable this to handle existing records gracefully
3. **Prefer Soft Delete**: Use `hard_delete: false` to allow recovery
4. **Monitor Results**: Always check the response for partial failures
5. **Batch Large Operations**: If you need to process more than 100 items, split into multiple requests

## Examples

### Python Example

```python
import httpx

async def bulk_create_users(token: str, users: list[dict]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/bulk/users/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "users": users,
                "skip_duplicates": True,
            },
        )
        return response.json()

# Usage
users = [
    {
        "email": "user1@example.com",
        "password": "SecurePass123!",
        "first_name": "User",
        "last_name": "One",
    },
    {
        "email": "user2@example.com",
        "password": "SecurePass456!",
        "first_name": "User",
        "last_name": "Two",
    },
]

result = await bulk_create_users(admin_token, users)
print(f"Created {result['successful']} users")
```

### JavaScript/TypeScript Example

```typescript
async function bulkDeactivateUsers(token: string, userIds: string[]) {
  const response = await fetch('/api/v1/bulk/users/status', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_ids: userIds,
      is_active: false,
    }),
  });
  
  return response.json();
}
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/bulk/users/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "users": [
      {
        "email": "user1@example.com",
        "password": "SecurePass123!",
        "first_name": "User",
        "last_name": "One"
      }
    ],
    "skip_duplicates": true
  }'
```

## Security Considerations

1. All bulk endpoints (except validate) require superuser privileges
2. Self-deletion is prevented in bulk delete operations
3. All operations are audited for compliance
4. Rate limiting applies to bulk endpoints
5. Maximum batch size is enforced to prevent DoS
