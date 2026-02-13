import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NotificationsPage from './NotificationsPage';

const mockGetAll = vi.fn();
const mockDelete = vi.fn();
const mockMarkAllAsRead = vi.fn();

vi.mock('@/services/api', () => ({
  notificationsService: {
    getAll: (...args: unknown[]) => mockGetAll(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
    markAllAsRead: (...args: unknown[]) => mockMarkAllAsRead(...args),
  },
}));

vi.mock('@/components/common/Modal', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  ConfirmModal: ({ isOpen, onConfirm, title }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        <h2>{title}</h2>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
}));

const mockMarkAsRead = vi.fn();
const mockStoreMarkAllAsRead = vi.fn();
const mockRemoveNotification = vi.fn();
const mockSetNotifications = vi.fn();

const mockNotifications = [
  {
    id: 'n1',
    title: 'New user registered',
    message: 'John Doe has registered.',
    type: 'info' as const,
    read: false,
    created_at: new Date(Date.now() - 60000).toISOString(), // 1 min ago
    action_url: '/users/1',
  },
  {
    id: 'n2',
    title: 'Backup completed',
    message: 'Database backup completed successfully.',
    type: 'success' as const,
    read: true,
    created_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
  },
  {
    id: 'n3',
    title: 'Disk space warning',
    message: 'Server is running low on disk space.',
    type: 'warning' as const,
    read: false,
    created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
  },
  {
    id: 'n4',
    title: 'Service error',
    message: 'Background task failed.',
    type: 'error' as const,
    read: true,
    created_at: new Date(Date.now() - 604800000).toISOString(), // 7 days ago
  },
];

vi.mock('@/stores/notificationsStore', () => ({
  useNotificationsStore: () => ({
    notifications: mockNotifications,
    unreadCount: mockNotifications.filter((n) => !n.read).length,
    markAsRead: mockMarkAsRead,
    markAllAsRead: mockStoreMarkAllAsRead,
    removeNotification: mockRemoveNotification,
    setNotifications: mockSetNotifications,
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <NotificationsPage />
    </MemoryRouter>,
  );
}

describe('NotificationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetAll.mockResolvedValue({ items: mockNotifications });
    mockDelete.mockResolvedValue({});
    mockMarkAllAsRead.mockResolvedValue({});
  });

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('notifications.title')).toBeInTheDocument();
  });

  it('shows unread count', () => {
    renderPage();
    expect(screen.getByText(/notifications.unreadCount/)).toBeInTheDocument();
  });

  it('displays notification titles', () => {
    renderPage();
    expect(screen.getByText('New user registered')).toBeInTheDocument();
    expect(screen.getByText('Backup completed')).toBeInTheDocument();
    expect(screen.getByText('Disk space warning')).toBeInTheDocument();
    expect(screen.getByText('Service error')).toBeInTheDocument();
  });

  it('displays notification messages', () => {
    renderPage();
    expect(screen.getByText('John Doe has registered.')).toBeInTheDocument();
    expect(screen.getByText('Database backup completed successfully.')).toBeInTheDocument();
  });

  it('shows filter tabs', () => {
    renderPage();
    expect(screen.getByText('notifications.all')).toBeInTheDocument();
    expect(screen.getByText('notifications.unread')).toBeInTheDocument();
    expect(screen.getByText('notifications.read')).toBeInTheDocument();
  });

  it('shows mark all read button when unread exist', () => {
    renderPage();
    expect(screen.getByText('notifications.markAllRead')).toBeInTheDocument();
  });

  it('shows refresh button', () => {
    renderPage();
    expect(screen.getByText('notifications.refresh')).toBeInTheDocument();
  });

  it('calls markAllAsRead on button click', async () => {
    renderPage();
    fireEvent.click(screen.getByText('notifications.markAllRead'));
    await waitFor(() => {
      expect(mockMarkAllAsRead).toHaveBeenCalled();
    });
    expect(mockStoreMarkAllAsRead).toHaveBeenCalled();
  });

  it('fetches notifications on mount', async () => {
    renderPage();
    await waitFor(() => {
      expect(mockGetAll).toHaveBeenCalledWith({ page: 1, page_size: 20 });
    });
  });

  it('shows relative time', () => {
    renderPage();
    // 1 min ago should show minutesAgo
    expect(screen.getByText('notifications.timeAgo.minutesAgo')).toBeInTheDocument();
  });

  it('deletes notification on delete button click', async () => {
    renderPage();
    const deleteButtons = screen.getAllByTitle('common.delete');
    fireEvent.click(deleteButtons[0]);
    // Confirm in the modal
    await waitFor(() => {
      expect(screen.getByTestId('confirm-modal')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Confirm'));
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('n1');
    });
    expect(mockRemoveNotification).toHaveBeenCalledWith('n1');
  });
});
