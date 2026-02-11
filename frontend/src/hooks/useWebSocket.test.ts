/**
 * Unit tests for useWebSocket hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from './useWebSocket';

// Mock authStore
let mockAccessToken: string | null = 'test-jwt-token.eyJleHAiOjk5OTk5OTk5OTl9.sig';

vi.mock('../stores/authStore', () => ({
  useAuthStore: (selector?: (s: any) => any) => {
    const state = {
      accessToken: mockAccessToken,
      refreshAccessToken: vi.fn().mockResolvedValue(undefined),
    };
    return selector ? selector(state) : state;
  },
}));

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  send = vi.fn();
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    mockWebSocketInstance = this;
  }
}

let mockWebSocketInstance: MockWebSocket | null = null;

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockWebSocketInstance = null;
    mockAccessToken = 'test-jwt-token.eyJleHAiOjk5OTk5OTk5OTl9.sig';
    
    // Replace global WebSocket with mock
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('should not be connected initially', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));
    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionId).toBeNull();
    expect(result.current.lastMessage).toBeNull();
  });

  it('should expose connect and disconnect functions', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));
    expect(typeof result.current.connect).toBe('function');
    expect(typeof result.current.disconnect).toBe('function');
    expect(typeof result.current.sendMessage).toBe('function');
    expect(typeof result.current.sendChatMessage).toBe('function');
    expect(typeof result.current.sendTyping).toBe('function');
    expect(typeof result.current.sendReadReceipt).toBe('function');
  });

  it('should connect when connect is called', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));
    
    act(() => {
      result.current.connect();
    });

    expect(mockWebSocketInstance).not.toBeNull();
    expect(mockWebSocketInstance!.url).toContain('ws:');
    // Token is sent via HttpOnly cookie, not in URL
    expect(mockWebSocketInstance!.url).not.toContain('token=');
  });

  it('should update isConnected on open', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    act(() => {
      result.current.connect();
    });

    act(() => {
      mockWebSocketInstance!.readyState = MockWebSocket.OPEN;
      mockWebSocketInstance!.onopen?.(new Event('open'));
    });

    expect(result.current.isConnected).toBe(true);
  });

  it('should handle disconnection', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    act(() => {
      result.current.connect();
    });

    act(() => {
      mockWebSocketInstance!.readyState = MockWebSocket.OPEN;
      mockWebSocketInstance!.onopen?.(new Event('open'));
    });

    expect(result.current.isConnected).toBe(true);

    act(() => {
      result.current.disconnect();
    });

    expect(result.current.isConnected).toBe(false);
    expect(mockWebSocketInstance!.close).toHaveBeenCalled();
  });

  it('should handle incoming messages', () => {
    const onNotification = vi.fn();
    const { result } = renderHook(() =>
      useWebSocket({ autoConnect: false, onNotification })
    );

    act(() => {
      result.current.connect();
    });

    act(() => {
      mockWebSocketInstance!.readyState = MockWebSocket.OPEN;
      mockWebSocketInstance!.onopen?.(new Event('open'));
    });

    const message = {
      type: 'notification',
      payload: { title: 'Test notification' },
    };

    act(() => {
      mockWebSocketInstance!.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify(message) })
      );
    });

    expect(result.current.lastMessage).toEqual(message);
    expect(onNotification).toHaveBeenCalledWith({ title: 'Test notification' });
  });

  it('should send message when connected', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    act(() => {
      result.current.connect();
    });

    act(() => {
      mockWebSocketInstance!.readyState = MockWebSocket.OPEN;
      mockWebSocketInstance!.onopen?.(new Event('open'));
    });

    act(() => {
      result.current.sendMessage({ type: 'ping', payload: {} });
    });

    expect(mockWebSocketInstance!.send).toHaveBeenCalledWith(
      JSON.stringify({
        type: 'ping',
        payload: {},
        recipient_id: undefined,
        room_id: undefined,
      })
    );
  });

  it('should send chat messages', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    act(() => {
      result.current.connect();
    });

    act(() => {
      mockWebSocketInstance!.readyState = MockWebSocket.OPEN;
      mockWebSocketInstance!.onopen?.(new Event('open'));
    });

    act(() => {
      result.current.sendChatMessage('Hello', 'user-2', 'room-1');
    });

    expect(mockWebSocketInstance!.send).toHaveBeenCalledWith(
      JSON.stringify({
        type: 'chat_message',
        payload: { content: 'Hello' },
        recipient_id: 'user-2',
        room_id: 'room-1',
      })
    );
  });

  it('should send typing indicator', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    act(() => {
      result.current.connect();
    });

    act(() => {
      mockWebSocketInstance!.readyState = MockWebSocket.OPEN;
      mockWebSocketInstance!.onopen?.(new Event('open'));
    });

    act(() => {
      result.current.sendTyping(true, 'user-2');
    });

    expect(mockWebSocketInstance!.send).toHaveBeenCalled();
  });

  it('should connect even without in-memory access token (cookies handle auth)', () => {
    mockAccessToken = null;
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

    act(() => {
      result.current.connect();
    });

    // Connection should still be created — auth is via HttpOnly cookies
    expect(mockWebSocketInstance).not.toBeNull();
  });

  it('should handle connected message with connectionId', () => {
    const onConnected = vi.fn();
    const { result } = renderHook(() =>
      useWebSocket({ autoConnect: false, onConnected })
    );

    act(() => {
      result.current.connect();
    });

    act(() => {
      mockWebSocketInstance!.readyState = MockWebSocket.OPEN;
      mockWebSocketInstance!.onopen?.(new Event('open'));
    });

    act(() => {
      mockWebSocketInstance!.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'connected',
            payload: { connection_id: 'conn-123' },
          }),
        })
      );
    });

    expect(result.current.connectionId).toBe('conn-123');
    expect(onConnected).toHaveBeenCalledWith('conn-123');
  });

  it('should handle presence messages', () => {
    const onPresenceChange = vi.fn();
    const { result } = renderHook(() =>
      useWebSocket({ autoConnect: false, onPresenceChange })
    );

    act(() => {
      result.current.connect();
    });

    act(() => {
      mockWebSocketInstance!.readyState = MockWebSocket.OPEN;
      mockWebSocketInstance!.onopen?.(new Event('open'));
    });

    act(() => {
      mockWebSocketInstance!.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'presence_online',
            payload: { user_id: 'user-5' },
          }),
        })
      );
    });

    expect(onPresenceChange).toHaveBeenCalledWith('user-5', 'online');
  });
});
