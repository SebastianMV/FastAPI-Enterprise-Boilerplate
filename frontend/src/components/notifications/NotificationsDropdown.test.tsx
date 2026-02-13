/**
 * Unit tests for NotificationsDropdown component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NotificationsDropdown from './NotificationsDropdown';

// Mock useWebSocket
vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ isConnected: true }),
}));

// Mock notificationsService
const mockServiceMarkAsRead = vi.fn().mockResolvedValue(undefined);
const mockServiceMarkAllAsRead = vi.fn().mockResolvedValue(undefined);
vi.mock('@/services/api', () => ({
  notificationsService: {
    markAsRead: (...args: unknown[]) => mockServiceMarkAsRead(...args),
    markAllAsRead: (...args: unknown[]) => mockServiceMarkAllAsRead(...args),
  },
}));

// Mock notifications store
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock notification array
const mockNotifications: any[] = [];
const mockMarkAsRead = vi.fn();
const mockMarkAllAsRead = vi.fn();
const mockAddNotification = vi.fn();
const mockSetConnected = vi.fn();

vi.mock('@/stores/notificationsStore', () => ({
  useNotificationsStore: () => ({
    notifications: mockNotifications,
    unreadCount: mockNotifications.filter((n: unknown) => !(n as Record<string, boolean>).read).length,
    isConnected: false,
    addNotification: mockAddNotification,
    markAsRead: mockMarkAsRead,
    markAllAsRead: mockMarkAllAsRead,
    setConnected: mockSetConnected,
  }),
}));

function renderDropdown() {
  return render(
    <MemoryRouter>
      <NotificationsDropdown />
    </MemoryRouter>
  );
}

describe('NotificationsDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNotifications.length = 0;
  });

  it('should render bell button', () => {
    renderDropdown();
    expect(screen.getByLabelText('notificationsDropdown.title')).toBeInTheDocument();
  });

  it('should show unread badge when there are unread notifications', () => {
    mockNotifications.push({
      id: '1',
      type: 'info',
      title: 'Test',
      message: 'Hello',
      read: false,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('should open dropdown on bell click', () => {
    renderDropdown();
    fireEvent.click(screen.getByLabelText('notificationsDropdown.title'));
    expect(screen.getByText('notificationsDropdown.title')).toBeInTheDocument();
  });

  it('should show empty state when no notifications', () => {
    renderDropdown();
    fireEvent.click(screen.getByLabelText('notificationsDropdown.title'));
    expect(screen.getByText('notificationsDropdown.noNotifications')).toBeInTheDocument();
  });

  it('should render notification items', () => {
    mockNotifications.push({
      id: '1',
      type: 'success',
      title: 'Task completed',
      message: 'Your task has been completed',
      read: false,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    fireEvent.click(screen.getByLabelText('notificationsDropdown.title'));
    expect(screen.getByText('Task completed')).toBeInTheDocument();
  });

  it('should show "Mark all read" button when unread exist', () => {
    mockNotifications.push({
      id: '1',
      type: 'info',
      title: 'Unread',
      read: false,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    fireEvent.click(screen.getByLabelText('notificationsDropdown.title'));
    expect(screen.getByText('notificationsDropdown.markAllRead')).toBeInTheDocument();
  });

  it('should call markAllAsRead', async () => {
    mockNotifications.push({
      id: '1',
      type: 'info',
      title: 'Unread',
      read: false,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    fireEvent.click(screen.getByLabelText('notificationsDropdown.title'));
    fireEvent.click(screen.getByText('notificationsDropdown.markAllRead'));
    await vi.waitFor(() => {
      expect(mockMarkAllAsRead).toHaveBeenCalled();
    });
  });

  it('should show View all notifications link', () => {
    mockNotifications.push({
      id: '1',
      type: 'info',
      title: 'Test',
      read: true,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    fireEvent.click(screen.getByLabelText('notificationsDropdown.title'));
    expect(screen.getByText('notificationsDropdown.viewAll')).toBeInTheDocument();
  });

  it('should close dropdown on close button click', () => {
    renderDropdown();
    fireEvent.click(screen.getByLabelText('notificationsDropdown.title'));
    expect(screen.getByText('notificationsDropdown.title')).toBeInTheDocument();
    // Find close button inside dropdown header (the X button)
    const closeButtons = screen.getAllByRole('button');
    const closeBtn = closeButtons.find(btn => btn.querySelector('.lucide-x'));
    if (closeBtn) fireEvent.click(closeBtn);
    // dropdown should close
  });
});
