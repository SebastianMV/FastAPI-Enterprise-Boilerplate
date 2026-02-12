/**
 * WebSocket hook for real-time communication.
 * 
 * Provides a simple interface to connect to the WebSocket server
 * and handle real-time messages.
 * 
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Authentication via HttpOnly cookies (auto-refresh)
 * - Typed message handlers with runtime validation
 * - Connection state management
 * - Ping/pong keep-alive
 * - Client-side message rate limiting
 * 
 * @example
 * ```tsx
 * const { isConnected, sendMessage, lastMessage } = useWebSocket({
 *   onNotification: (payload) => handleNotification(payload),
 *   onPresenceChange: (userId, status) => updatePresence(userId, status),
 * });
 * ```
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { useAuthStore } from '../stores/authStore';
import { sanitizeText } from '../utils/security';

// Debug logging - only in development
const DEBUG = import.meta.env.DEV;
const debugLog = (...args: unknown[]) => DEBUG && console.log(...args);

// Message types matching backend
export type MessageType =
  | 'connected'
  | 'disconnected'
  | 'error'
  | 'ping'
  | 'pong'
  | 'notification'
  | 'notification_read'
  | 'chat_message'
  | 'chat_typing'
  | 'chat_read'
  | 'chat_delivered'
  | 'presence_online'
  | 'presence_offline'
  | 'presence_away'
  | 'broadcast'
  | 'tenant_broadcast';

const VALID_MESSAGE_TYPES = new Set<string>([
  'connected', 'disconnected', 'error', 'ping', 'pong',
  'notification', 'notification_read', 'chat_message',
  'chat_typing', 'chat_read', 'chat_delivered',
  'presence_online', 'presence_offline', 'presence_away',
  'broadcast', 'tenant_broadcast',
]);

export interface WebSocketMessage {
  type: MessageType;
  payload: Record<string, unknown>;
  sender_id?: string;
  recipient_id?: string;
  room_id?: string;
  timestamp?: string;
  message_id?: string;
}

export interface UseWebSocketOptions {
  /** Custom WebSocket URL (defaults to /ws which nginx proxies to backend /api/v1/ws) */
  url?: string;
  /** Auto-connect on mount */
  autoConnect?: boolean;
  /** Reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect delay in ms */
  reconnectDelay?: number;
  /** Max reconnect attempts */
  maxReconnectAttempts?: number;
  /** Ping interval in ms */
  pingInterval?: number;
  
  // Event handlers
  onConnected?: (connectionId: string) => void;
  onDisconnected?: () => void;
  onError?: (error: Error) => void;
  onNotification?: (payload: Record<string, unknown>) => void;
  onChatMessage?: (payload: Record<string, unknown>) => void;
  onPresenceChange?: (userId: string, status: 'online' | 'offline' | 'away') => void;
  onTyping?: (userId: string, isTyping: boolean, roomId?: string) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export interface UseWebSocketReturn {
  /** Connection state */
  isConnected: boolean;
  /** Connection ID (assigned by server) */
  connectionId: string | null;
  /** Last received message */
  lastMessage: WebSocketMessage | null;
  /** Connect to WebSocket server */
  connect: () => void;
  /** Disconnect from WebSocket server */
  disconnect: () => void;
  /** Send a message */
  sendMessage: (message: Partial<WebSocketMessage>) => void;
  /** Send a chat message */
  sendChatMessage: (content: string, recipientId?: string, roomId?: string) => void;
  /** Send typing indicator */
  sendTyping: (isTyping: boolean, recipientId?: string, roomId?: string) => void;
  /** Send read receipt */
  sendReadReceipt: (messageIds: string[], senderId: string) => void;
}

const DEFAULT_OPTIONS: Required<Omit<UseWebSocketOptions, 
  'onConnected' | 'onDisconnected' | 'onError' | 'onNotification' | 
  'onChatMessage' | 'onPresenceChange' | 'onTyping' | 'onMessage'
>> = {
  url: '',
  autoConnect: true,
  autoReconnect: true,
  reconnectDelay: 3000,
  maxReconnectAttempts: 10,
  pingInterval: 30000,
};

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  // Memoize options to prevent changing on every render
  // Callbacks are excluded from deps to prevent unnecessary re-renders
  const opts = useMemo(() => ({
    ...DEFAULT_OPTIONS,
    ...options
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [
    options.url,
    options.autoConnect,
    options.autoReconnect,
    options.reconnectDelay,
    options.maxReconnectAttempts,
    options.pingInterval,
  ]);
  
  const { tokenExpiresAt } = useAuthStore();
  const refreshAccessToken = useAuthStore((state) => state.refreshAccessToken);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const optionsRef = useRef(options);
  const isIntentionalCloseRef = useRef(false);
  
  // Keep options ref up to date without triggering reconnections
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);
  
  // Build WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    if (opts.url) return opts.url;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    // Use /ws path - nginx will proxy to backend /api/v1/ws
    // Token is sent via HttpOnly cookie (withCredentials), not in URL query param
    return `${protocol}//${host}/ws`;
  }, [opts.url]);
  
  // Handle incoming messages with runtime validation
  const handleMessage = useCallback((event: MessageEvent) => {
    // Reject oversized messages to prevent memory exhaustion
    if (typeof event.data === 'string' && event.data.length > 1_000_000) {
      debugLog('[WebSocket] Dropped oversized message:', event.data.length, 'bytes');
      return;
    }
    try {
      const parsed = JSON.parse(event.data);
      
      // Runtime validation: ensure message has required structure
      if (
        typeof parsed !== 'object' ||
        parsed === null ||
        typeof parsed.type !== 'string' ||
        !VALID_MESSAGE_TYPES.has(parsed.type)
      ) {
        return; // Drop malformed or unknown-type messages
      }
      
      // Ensure payload is an object
      if (typeof parsed.payload !== 'object' || parsed.payload === null) {
        parsed.payload = {};
      }
      
      const message: WebSocketMessage = {
        type: parsed.type as MessageType,
        payload: parsed.payload,
        sender_id: typeof parsed.sender_id === 'string' ? parsed.sender_id : undefined,
        recipient_id: typeof parsed.recipient_id === 'string' ? parsed.recipient_id : undefined,
        room_id: typeof parsed.room_id === 'string' ? parsed.room_id : undefined,
        timestamp: typeof parsed.timestamp === 'string' ? parsed.timestamp : undefined,
        message_id: typeof parsed.message_id === 'string' ? parsed.message_id : undefined,
      };
      
      setLastMessage(message);
      
      // Call general message handler
      optionsRef.current.onMessage?.(message);
      
      // Handle specific message types
      switch (message.type) {
        case 'connected': {
          const connId = message.payload.connection_id;
          if (typeof connId === 'string') {
            setConnectionId(connId);
            optionsRef.current.onConnected?.(connId);
          }
          break;
        }
          
        case 'notification':
          optionsRef.current.onNotification?.(message.payload);
          break;
          
        case 'chat_message':
          optionsRef.current.onChatMessage?.(message.payload);
          break;
          
        case 'presence_online': {
          const userId = message.payload.user_id;
          if (typeof userId === 'string') {
            optionsRef.current.onPresenceChange?.(userId, 'online');
          }
          break;
        }
          
        case 'presence_offline': {
          const userId = message.payload.user_id;
          if (typeof userId === 'string') {
            optionsRef.current.onPresenceChange?.(userId, 'offline');
          }
          break;
        }
          
        case 'presence_away': {
          const userId = message.payload.user_id;
          if (typeof userId === 'string') {
            optionsRef.current.onPresenceChange?.(userId, 'away');
          }
          break;
        }
          
        case 'chat_typing': {
          const userId = message.payload.user_id;
          const isTyping = message.payload.is_typing;
          if (typeof userId === 'string' && typeof isTyping === 'boolean') {
            optionsRef.current.onTyping?.(userId, isTyping, message.room_id);
          }
          break;
        }
          
        case 'error':
          optionsRef.current.onError?.(new Error('WebSocket server error'));
          break;
      }
    } catch {
      // Failed to parse WebSocket message — don't log payload in production
    }
  }, []);
  
  // Start ping interval
  const startPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'ping',
          payload: { timestamp: Date.now() },
        }));
      }
    }, opts.pingInterval);
  }, [opts.pingInterval]);
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    // Auth is handled via HttpOnly cookies — no need to check accessToken in memory.
    // The browser will send cookies automatically on the WebSocket handshake.
    
    // Don't reconnect if already connected or connecting
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        debugLog('[WebSocket] Already connected, skipping');
        return;
      }
      if (wsRef.current.readyState === WebSocket.CONNECTING) {
        debugLog('[WebSocket] Already connecting, skipping');
        return;
      }
    }
    
    isIntentionalCloseRef.current = false;
    debugLog('[WebSocket] Initiating connection...');
    
    try {
      const ws = new WebSocket(getWebSocketUrl());
      wsRef.current = ws;
      
      ws.onopen = () => {
        debugLog('[WebSocket] Connection opened successfully');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        startPingInterval();
      };
      
      ws.onmessage = handleMessage;
      
      ws.onclose = (event) => {
        debugLog('[WebSocket] Connection closed:', event.code, 'intentional:', isIntentionalCloseRef.current);
        setIsConnected(false);
        setConnectionId(null);
        optionsRef.current.onDisconnected?.();
        
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        
        // 403/1008 = Policy Violation (likely auth issue)
        if (event.code === 1008 && !isIntentionalCloseRef.current) {
          // Check against maxReconnectAttempts to prevent infinite loop
          if (reconnectAttemptsRef.current >= opts.maxReconnectAttempts) {
            optionsRef.current.onError?.(new Error('WebSocket max reconnect attempts reached'));
            return;
          }
          debugLog('[WebSocket] Authentication failed, attempting token refresh...');
          refreshAccessToken().then(() => {
            debugLog('[WebSocket] Token refreshed, reconnecting...');
            reconnectAttemptsRef.current++;
            setTimeout(() => connect(), 1000);
          }).catch(() => {
            // Token refresh failed — notify via callback
            optionsRef.current.onError?.(new Error('WebSocket authentication failed'));
          });
          return;
        }
        
        // Auto-reconnect only if not intentional close
        if (!isIntentionalCloseRef.current && opts.autoReconnect && reconnectAttemptsRef.current < opts.maxReconnectAttempts) {
          // Exponential backoff with jitter: delay * 2^attempts + random jitter
          const backoffDelay = Math.min(
            opts.reconnectDelay * Math.pow(2, reconnectAttemptsRef.current) + Math.random() * 1000,
            60000 // Cap at 60 seconds
          );
          debugLog('[WebSocket] Scheduling reconnect attempt', reconnectAttemptsRef.current + 1, 'in', Math.round(backoffDelay), 'ms');
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, backoffDelay);
        }
      };
      
      ws.onerror = () => {
        // WebSocket errors are expected when server is not running
        // Silently notify via callback, avoid console noise
        optionsRef.current.onError?.(new Error('WebSocket connection error'));
      };
    } catch (error) {
      // Silently notify via callback
      optionsRef.current.onError?.(error instanceof Error ? error : new Error('WebSocket connection failed'));
    }
  }, [getWebSocketUrl, handleMessage, startPingInterval, refreshAccessToken, opts]);
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    isIntentionalCloseRef.current = true;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionId(null);
  }, []);
  
  // Rate limiting for outgoing messages
  const lastSendTimestamps = useRef<number[]>([]);
  const MAX_MESSAGES_PER_SECOND = 10;
  
  const isRateLimited = useCallback((): boolean => {
    const now = Date.now();
    // Remove timestamps older than 1 second
    lastSendTimestamps.current = lastSendTimestamps.current.filter(t => now - t < 1000);
    if (lastSendTimestamps.current.length >= MAX_MESSAGES_PER_SECOND) {
      return true;
    }
    lastSendTimestamps.current.push(now);
    return false;
  }, []);
  
  // Send a message
  const sendMessage = useCallback((message: Partial<WebSocketMessage>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // Validate outbound message type against known types
      if (message.type && !VALID_MESSAGE_TYPES.has(message.type)) {
        return;
      }
      if (isRateLimited()) {
        if (DEBUG) {
          console.warn('WebSocket message rate limited');
        }
        return;
      }
      // Sanitize string values in payload to prevent stored-XSS via server relay
      const sanitizedPayload: Record<string, unknown> = {};
      const rawPayload = (message.payload || {}) as Record<string, unknown>;
      for (const [key, val] of Object.entries(rawPayload)) {
        sanitizedPayload[key] = typeof val === 'string' ? sanitizeText(val) : val;
      }
      wsRef.current.send(JSON.stringify({
        type: message.type,
        payload: sanitizedPayload,
        recipient_id: message.recipient_id,
        room_id: message.room_id,
      }));
    } else {
      if (DEBUG) {
        console.warn('Cannot send message: WebSocket not connected');
      }
    }
  }, [isRateLimited]);
  
  // Send a chat message (with content sanitization)
  const sendChatMessage = useCallback((
    content: string,
    recipientId?: string,
    roomId?: string,
  ) => {
    sendMessage({
      type: 'chat_message',
      payload: { content: sanitizeText(content) },
      recipient_id: recipientId,
      room_id: roomId,
    });
  }, [sendMessage]);
  
  // Send typing indicator
  const sendTyping = useCallback((
    isTyping: boolean,
    recipientId?: string,
    roomId?: string,
  ) => {
    sendMessage({
      type: 'chat_typing',
      payload: { is_typing: isTyping },
      recipient_id: recipientId,
      room_id: roomId,
    });
  }, [sendMessage]);
  
  // Send read receipt
  const sendReadReceipt = useCallback((messageIds: string[], senderId: string) => {
    // Cap IDs to prevent oversized payloads
    const cappedIds = messageIds.slice(0, 100);
    sendMessage({
      type: 'chat_read',
      payload: { message_ids: cappedIds },
      recipient_id: senderId,
    });
  }, [sendMessage]);
  
  // Auto-connect on mount
  useEffect(() => {
    if (!opts.autoConnect || !isAuthenticated) {
      return;
    }
    
    // Check if token is expired or about to expire (within 1 minute)
    const checkTokenAndConnect = async () => {
      try {
        // If we have an expiry timestamp, check if token is about to expire
        if (tokenExpiresAt) {
          const now = Date.now();
          const timeUntilExpiry = tokenExpiresAt - now;
          
          if (timeUntilExpiry < 60000) {
            debugLog('[WebSocket] Token expiring soon, refreshing before connect...');
            await refreshAccessToken();
            // Fall through to connect() after refresh instead of returning
          }
        }
      } catch {
        // Token expiry check failed — proceed with connection anyway
      }
      
      // Proceed with connection (cookies will provide auth)
      connect();
    };
    
    // Small delay to avoid rapid connect/disconnect in React Strict Mode
    const connectTimer = setTimeout(() => {
      checkTokenAndConnect();
    }, 100);
    
    return () => {
      clearTimeout(connectTimer);
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.autoConnect, isAuthenticated]);
  
  return {
    isConnected,
    connectionId,
    lastMessage,
    connect,
    disconnect,
    sendMessage,
    sendChatMessage,
    sendTyping,
    sendReadReceipt,
  };
}
