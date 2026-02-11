# WebSocket Architecture

## Overview

Simple WebSocket architecture for **real-time notifications**:

- 🔔 **Real-time Notifications** - Instant delivery to connected clients
- 📊 **Live Dashboard Updates** - Real-time metrics and status changes
- 👤 **Presence Tracking** - Online/offline status of users

## Configuration

Control WebSocket features via environment variables:

```bash
WEBSOCKET_ENABLED=true              # Enable/disable WebSocket functionality
WEBSOCKET_NOTIFICATIONS=true        # Enable real-time notifications
```

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Browser  │  │ Mobile   │  │ Desktop  │  │   API    │        │
│  │   App    │  │   App    │  │   App    │  │  Client  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       └─────────────┴─────────────┴─────────────┘               │
│                           │                                     │
│                  WebSocket Connections                          │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI WebSocket Endpoints                   │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │        /ws           │  │  /ws/notifications   │            │
│  │       (main)         │  │    (read-only)       │            │
│  └──────────┬───────────┘  └──────────┬───────────┘            │
│             └────────────┬────────────┘                         │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                MemoryWebSocketManager                     │  │
│  │              (in-memory, single instance)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## WebSocket Endpoints

### Main WebSocket (`/api/v1/ws`)

Full-featured WebSocket supporting all message types.

```typescript
// Connect with JWT token
const ws = new WebSocket(`wss://api.example.com/api/v1/ws?token=${accessToken}`);

// Handle messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  switch (message.type) {
    case 'notification':
      handleNotification(message.payload);
      break;
  }
};
```

### Notifications Only (`/api/v1/ws/notifications`)

Read-only WebSocket for receiving notifications.

```typescript
const ws = new WebSocket(`wss://api.example.com/api/v1/ws/notifications?token=${accessToken}`);
```

## Message Types

### Incoming (Client → Server)

| Type | Description | Payload |
|------|-------------|---------|
| `ping` | Keep-alive | `{}` |

### Outgoing (Server → Client)

| Type | Description | Payload |
|------|-------------|---------|
| `pong` | Keep-alive response | `{ timestamp }` |
| `notification` | New notification | `{ id, type, title, message, priority, data? }` |

## Frontend Integration

### React Hooks

#### useWebSocket

Core WebSocket connection with auto-reconnect:

```tsx
import { useWebSocket } from '@/hooks/useWebSocket';

function NotificationBell() {
  const { isConnected, lastMessage } = useWebSocket({
    onNotification: (notification) => {
      toast.success(notification.title);
    },
  });
  
  return (
    <div className={isConnected ? 'text-green-500' : 'text-red-500'}>
      {isConnected ? '🟢' : '🔴'}
    </div>
  );
}
```

#### useNotifications

Notifications management with REST API + WebSocket:

```tsx
import { useNotifications } from '@/hooks/useNotifications';

function NotificationList() {
  const { 
    notifications, 
    unreadCount, 
    markAsRead, 
    markAllAsRead 
  } = useNotifications();
  
  return (
    <div>
      <h2>Notifications ({unreadCount})</h2>
      <button onClick={markAllAsRead}>Mark all as read</button>
      {notifications.map(n => (
        <div key={n.id} onClick={() => markAsRead(n.id)}>
          {n.title}
        </div>
      ))}
    </div>
  );
}
```

## REST API Endpoints

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/notifications` | List notifications |
| `GET` | `/api/v1/notifications/unread/count` | Get unread count |
| `GET` | `/api/v1/notifications/{id}` | Get notification |
| `POST` | `/api/v1/notifications/read` | Mark as read |
| `POST` | `/api/v1/notifications/read/all` | Mark all as read |
| `DELETE` | `/api/v1/notifications/{id}` | Delete notification |
| `DELETE` | `/api/v1/notifications/read` | Delete read notifications |

## Database Schema

### Notifications

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    channel VARCHAR(20) DEFAULT 'in_app',
    data JSONB,
    action_url VARCHAR(500),
    read_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    delivery_status VARCHAR(20) DEFAULT 'pending',
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE
);
```

## Production Deployment

### Load Balancer Configuration

For WebSocket connections, configure sticky sessions:

```nginx
# nginx.conf
upstream api {
    ip_hash;  # Sticky sessions for WebSocket
    server api:8000;
}

server {
    location /api/v1/ws {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;  # 24 hours
    }
}
```

## Sending Notifications (Backend)

### Using NotificationService

```python
from app.application.services.notification_service import NotificationService
from app.infrastructure.database.connection import get_session

async def send_welcome_notification(user_id: UUID, tenant_id: UUID):
    async with get_session() as session:
        notification_service = NotificationService(session)
        
        await notification_service.notify_welcome(
            user_id=user_id,
            tenant_id=tenant_id,
        )
```

### Custom Notifications

```python
from app.domain.entities.notification import NotificationType, NotificationPriority

await notification_service.create_notification(
    user_id=user_id,
    tenant_id=tenant_id,
    type=NotificationType.SYSTEM_ALERT,
    title="System Maintenance",
    message="Scheduled maintenance in 30 minutes",
    priority=NotificationPriority.HIGH,
    data={"scheduled_at": "2025-01-15T10:00:00Z"},
    action_url="/settings/maintenance",
    send_realtime=True,  # Send via WebSocket
)
```

## Security Considerations

1. **Authentication**: WebSocket connections require valid JWT token via query parameter
2. **Rate Limiting**: Consider implementing per-connection rate limits
3. **Message Sanitization**: Always sanitize user-generated content
4. **Tenant Isolation**: RLS ensures data isolation at database level

## Monitoring

### Connection Metrics

```python
# Get WebSocket stats
manager = get_websocket_manager()
stats = manager.get_stats()
print(f"Total connections: {stats['total_connections']}")
print(f"Total users: {stats['total_users']}")
```

### Health Check

The `/api/v1/health` endpoint includes WebSocket status when enabled.

## Troubleshooting

### Connection Issues

1. Verify JWT token is valid
2. Check CORS configuration allows WebSocket upgrades
3. Verify load balancer supports WebSocket protocol

### Message Delivery Issues

1. Check user is connected (`await manager.is_user_online(user_id)`)
2. Verify tenant isolation matches
