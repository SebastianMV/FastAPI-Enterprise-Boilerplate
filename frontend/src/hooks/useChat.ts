/**
 * Chat hook for real-time messaging.
 * 
 * Provides a complete chat interface with:
 * - Real-time message delivery
 * - Typing indicators
 * - Read receipts
 * - Message history
 * 
 * @example
 * ```tsx
 * const { messages, sendMessage, isTyping } = useChat(conversationId);
 * ```
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { chatService, type ChatMessage, type Conversation } from '../services/api';

// Re-export types for convenience
export type { ChatMessage, Conversation };

// ChatMessage and Conversation types are now imported from api.ts

export interface TypingUser {
  userId: string;
  startedAt: number;
}

export interface UseChatOptions {
  /** Auto-fetch messages on mount */
  autoFetch?: boolean;
  /** Number of messages to fetch */
  messageLimit?: number;
  /** Typing indicator timeout (ms) */
  typingTimeout?: number;
}

export interface UseChatReturn {
  /** Chat messages */
  messages: ChatMessage[];
  /** Loading state */
  isLoading: boolean;
  /** Error message */
  error: string | null;
  /** WebSocket connected */
  isConnected: boolean;
  /** Users currently typing */
  typingUsers: TypingUser[];
  /** Send a message */
  sendMessage: (content: string, replyToId?: string) => Promise<void>;
  /** Send typing indicator */
  setTyping: (isTyping: boolean) => void;
  /** Mark messages as read */
  markAsRead: (messageIds: string[]) => Promise<void>;
  /** Load more messages (older) */
  loadMore: () => Promise<void>;
  /** Has more messages to load */
  hasMore: boolean;
  /** Refresh messages */
  refresh: () => Promise<void>;
}

export function useChat(
  conversationId: string | null,
  options: UseChatOptions = {}
): UseChatReturn {
  const { autoFetch = true, messageLimit = 50, typingTimeout = 3000 } = options;
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [typingUsers, setTypingUsers] = useState<TypingUser[]>([]);
  const [hasMore, setHasMore] = useState(true);
  
  const typingTimeoutRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const isTypingRef = useRef(false);
  
  // Handle incoming chat message
  const handleChatMessage = useCallback((payload: Record<string, unknown>) => {
    const message = payload as unknown as ChatMessage;
    
    // Only add if for current conversation
    if (message.conversation_id === conversationId) {
      setMessages((prev) => {
        // Check for duplicate
        if (prev.some((m) => m.id === message.id)) {
          return prev;
        }
        return [...prev, message];
      });
    }
  }, [conversationId]);
  
  // Handle typing indicator
  const handleTyping = useCallback((
    userId: string,
    isTyping: boolean,
    roomId?: string
  ) => {
    // Only process if for current conversation
    if (roomId !== conversationId) return;
    
    // Clear existing timeout
    const existingTimeout = typingTimeoutRef.current.get(userId);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
      typingTimeoutRef.current.delete(userId);
    }
    
    if (isTyping) {
      // Add to typing users
      setTypingUsers((prev) => {
        if (prev.some((u) => u.userId === userId)) {
          return prev;
        }
        return [...prev, { userId, startedAt: Date.now() }];
      });
      
      // Set timeout to remove
      const timeout = setTimeout(() => {
        setTypingUsers((prev) => prev.filter((u) => u.userId !== userId));
        typingTimeoutRef.current.delete(userId);
      }, typingTimeout);
      
      typingTimeoutRef.current.set(userId, timeout);
    } else {
      // Remove from typing users
      setTypingUsers((prev) => prev.filter((u) => u.userId !== userId));
    }
  }, [conversationId, typingTimeout]);
  
  // WebSocket connection
  const { isConnected, sendTyping: wsSendTyping } = useWebSocket({
    onChatMessage: handleChatMessage,
    onTyping: handleTyping,
  });
  
  // Fetch messages from API
  const fetchMessages = useCallback(async (before?: string) => {
    if (!conversationId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await chatService.getMessages(conversationId, {
        limit: messageLimit,
        before,
      });
      
      if (before) {
        // Prepend older messages
        setMessages((prev) => [...response.items, ...prev]);
      } else {
        setMessages(response.items);
      }
      
      setHasMore(response.has_more);
    } catch (err) {
      setError('Failed to fetch messages');
      console.error('Error fetching messages:', err);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, messageLimit]);
  
  // Send typing indicator
  const setTyping = useCallback((typing: boolean) => {
    if (!conversationId) return;
    
    if (typing !== isTypingRef.current) {
      isTypingRef.current = typing;
      wsSendTyping(typing, undefined, conversationId);
    }
  }, [conversationId, wsSendTyping]);
  
  // Send a message
  const sendMessage = useCallback(async (content: string, replyToId?: string) => {
    if (!conversationId || !content.trim()) return;
    
    try {
      // Send via REST API for persistence
      const message = await chatService.sendMessage(conversationId, {
        content,
        reply_to_id: replyToId,
      });
      
      // Add to local state (WebSocket will also deliver it)
      setMessages((prev) => {
        if (prev.some((m) => m.id === message.id)) {
          return prev;
        }
        return [...prev, message];
      });
      
      // Stop typing
      if (isTypingRef.current) {
        setTyping(false);
      }
    } catch (err) {
      console.error('Error sending message:', err);
      throw err;
    }
  }, [conversationId, setTyping]);
  
  // Mark messages as read
  const markAsRead = useCallback(async (messageIds: string[]) => {
    if (!conversationId || messageIds.length === 0) return;
    
    try {
      await chatService.markAsRead(conversationId, messageIds);
      
      // Update local state
      setMessages((prev) =>
        prev.map((m) =>
          messageIds.includes(m.id) ? { ...m, status: 'read' as const } : m
        )
      );
    } catch (err) {
      console.error('Error marking messages as read:', err);
    }
  }, [conversationId]);
  
  // Load more messages
  const loadMore = useCallback(async () => {
    if (!hasMore || isLoading || messages.length === 0) return;
    
    const oldestMessage = messages[0];
    await fetchMessages(oldestMessage.created_at);
  }, [hasMore, isLoading, messages, fetchMessages]);
  
  // Refresh messages
  const refresh = useCallback(async () => {
    setMessages([]);
    setHasMore(true);
    await fetchMessages();
  }, [fetchMessages]);
  
  // Auto-fetch on mount or conversation change
  useEffect(() => {
    if (autoFetch && conversationId) {
      setMessages([]);
      setHasMore(true);
      setTypingUsers([]);
      fetchMessages();
    }
  }, [autoFetch, conversationId, fetchMessages]);
  
  // Cleanup typing timeouts
  useEffect(() => {
    const timeoutsMap = typingTimeoutRef.current;
    return () => {
      timeoutsMap.forEach((timeout) => clearTimeout(timeout));
      timeoutsMap.clear();
    };
  }, []);
  
  return {
    messages,
    isLoading,
    error,
    isConnected,
    typingUsers,
    sendMessage,
    setTyping,
    markAsRead,
    loadMore,
    hasMore,
    refresh,
  };
}

/**
 * Hook for managing conversations list.
 */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fetchConversations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const conversationsList = await chatService.getConversations();
      setConversations(conversationsList);
    } catch (err) {
      setError('Failed to fetch conversations');
      console.error('Error fetching conversations:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const createDirectConversation = useCallback(async (userId: string) => {
    try {
      const conversation = await chatService.createDirectConversation(userId);
      
      setConversations((prev) => [conversation, ...prev]);
      return conversation;
    } catch (err) {
      console.error('Error creating conversation:', err);
      throw err;
    }
  }, []);
  
  const createGroupConversation = useCallback(async (
    name: string,
    participantIds: string[]
  ) => {
    try {
      const conversation = await chatService.createGroupConversation(name, participantIds);
      
      setConversations((prev) => [conversation, ...prev]);
      return conversation;
    } catch (err) {
      console.error('Error creating group:', err);
      throw err;
    }
  }, []);
  
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);
  
  return {
    conversations,
    isLoading,
    error,
    fetchConversations,
    createDirectConversation,
    createGroupConversation,
  };
}
