/**
 * WebSocket hook for real-time communication.
 * 
 * Provides a simple interface to connect to the WebSocket server
 * and handle real-time messages.
 * 
 * Features:
 * - Automatic reconnection
 * - Authentication via JWT token
 * - Message type handlers
 * - Connection state management
 * 
 * @example
 * ```tsx
 * const { isConnected, sendMessage, lastMessage } = useWebSocket({
 *   onNotification: (payload) => console.log('Notification:', payload),
 *   onChatMessage: (payload) => console.log('Chat:', payload),
 * });
 * ```
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { useAuthStore } from '../stores/authStore';

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
  /** Custom WebSocket URL (defaults to /api/v1/ws) */
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
  
  const { accessToken } = useAuthStore();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  // Build WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    if (opts.url) return opts.url;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/api/v1/ws?token=${accessToken}`;
  }, [opts.url, accessToken]);
  
  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      setLastMessage(message);
      
      // Call general message handler
      options.onMessage?.(message);
      
      // Handle specific message types
      switch (message.type) {
        case 'connected':
          setConnectionId(message.payload.connection_id as string);
          options.onConnected?.(message.payload.connection_id as string);
          break;
          
        case 'notification':
          options.onNotification?.(message.payload);
          break;
          
        case 'chat_message':
          options.onChatMessage?.(message.payload);
          break;
          
        case 'presence_online':
          options.onPresenceChange?.(message.payload.user_id as string, 'online');
          break;
          
        case 'presence_offline':
          options.onPresenceChange?.(message.payload.user_id as string, 'offline');
          break;
          
        case 'presence_away':
          options.onPresenceChange?.(message.payload.user_id as string, 'away');
          break;
          
        case 'chat_typing':
          options.onTyping?.(
            message.payload.user_id as string,
            message.payload.is_typing as boolean,
            message.room_id,
          );
          break;
          
        case 'error':
          options.onError?.(new Error(message.payload.message as string));
          break;
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }, [options]);
  
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
    if (!accessToken) {
      console.warn('Cannot connect to WebSocket: No access token');
      return;
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    try {
      const ws = new WebSocket(getWebSocketUrl());
      wsRef.current = ws;
      
      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        startPingInterval();
      };
      
      ws.onmessage = handleMessage;
      
      ws.onclose = () => {
        setIsConnected(false);
        setConnectionId(null);
        options.onDisconnected?.();
        
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        
        // Auto-reconnect
        if (opts.autoReconnect && reconnectAttemptsRef.current < opts.maxReconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, opts.reconnectDelay);
        }
      };
      
      ws.onerror = () => {
        // WebSocket errors are expected when server is not running
        // Silently notify via callback, avoid console noise
        options.onError?.(new Error('WebSocket connection error'));
      };
    } catch (error) {
      // Silently notify via callback
      options.onError?.(error as Error);
    }
  }, [accessToken, getWebSocketUrl, handleMessage, startPingInterval, opts, options]);
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionId(null);
  }, []);
  
  // Send a message
  const sendMessage = useCallback((message: Partial<WebSocketMessage>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: message.type,
        payload: message.payload || {},
        recipient_id: message.recipient_id,
        room_id: message.room_id,
      }));
    } else {
      console.warn('Cannot send message: WebSocket not connected');
    }
  }, []);
  
  // Send a chat message
  const sendChatMessage = useCallback((
    content: string,
    recipientId?: string,
    roomId?: string,
  ) => {
    sendMessage({
      type: 'chat_message',
      payload: { content },
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
    sendMessage({
      type: 'chat_read',
      payload: { message_ids: messageIds },
      recipient_id: senderId,
    });
  }, [sendMessage]);
  
  // Auto-connect on mount
  useEffect(() => {
    if (opts.autoConnect && accessToken) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [opts.autoConnect, accessToken, connect, disconnect]);
  
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
