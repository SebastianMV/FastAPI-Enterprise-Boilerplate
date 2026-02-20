import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import NotificationsPage from "./NotificationsPage";

const mockGetAll = vi.fn();
const mockDelete = vi.fn();
const mockMarkAllAsRead = vi.fn();

vi.mock("@/services/api", () => ({
  notificationsService: {
    getAll: (...args: unknown[]) => mockGetAll(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
    markAllAsRead: (...args: unknown[]) => mockMarkAllAsRead(...args),
  },
}));

vi.mock("@/components/common/Modal", () => ({
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
    id: "n1",
    title: "New user registered",
    message: "John Doe has registered.",
    type: "info" as const,
    read: false,
    created_at: new Date(Date.now() - 60000).toISOString(), // 1 min ago
    action_url: "/users/1",
  },
  {
    id: "n2",
    title: "Backup completed",
    message: "Database backup completed successfully.",
    type: "success" as const,
    read: true,
    created_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
  },
  {
    id: "n3",
    title: "Disk space warning",
    message: "Server is running low on disk space.",
    type: "warning" as const,
    read: false,
    created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
  },
  {
    id: "n4",
    title: "Service error",
    message: "Background task failed.",
    type: "error" as const,
    read: true,
    created_at: new Date(Date.now() - 604800000).toISOString(), // 7 days ago
  },
];

vi.mock("@/stores/notificationsStore", () => ({
  useNotificationsStore: () => ({
    notifications: mockNotifications,
    unreadCount: mockNotifications.filter((n) => !n.read).length,
    markAsRead: mockMarkAsRead,
    markAllAsRead: mockStoreMarkAllAsRead,
    removeNotification: mockRemoveNotification,
    setNotifications: mockSetNotifications,
  }),
}));

async function renderPage() {
  const view = render(
    <MemoryRouter>
      <NotificationsPage />
    </MemoryRouter>,
  );

  await waitFor(() => {
    expect(mockGetAll).toHaveBeenCalledWith({ page: 1, page_size: 20 });
  });

  return view;
}

describe("NotificationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetAll.mockResolvedValue({ items: mockNotifications });
    mockDelete.mockResolvedValue({});
    mockMarkAllAsRead.mockResolvedValue({});
  });

  it("renders page title", async () => {
    await renderPage();
    expect(screen.getByText("notifications.title")).toBeInTheDocument();
  });

  it("shows unread count", async () => {
    await renderPage();
    expect(screen.getByText(/notifications.unreadCount/)).toBeInTheDocument();
  });

  it("displays notification titles", async () => {
    await renderPage();
    expect(screen.getByText("New user registered")).toBeInTheDocument();
    expect(screen.getByText("Backup completed")).toBeInTheDocument();
    expect(screen.getByText("Disk space warning")).toBeInTheDocument();
    expect(screen.getByText("Service error")).toBeInTheDocument();
  });

  it("displays notification messages", async () => {
    await renderPage();
    expect(screen.getByText("John Doe has registered.")).toBeInTheDocument();
    expect(
      screen.getByText("Database backup completed successfully."),
    ).toBeInTheDocument();
  });

  it("shows filter tabs", async () => {
    await renderPage();
    expect(screen.getByText("notifications.all")).toBeInTheDocument();
    expect(screen.getByText("notifications.unread")).toBeInTheDocument();
    expect(screen.getByText("notifications.read")).toBeInTheDocument();
  });

  it("shows mark all read button when unread exist", async () => {
    await renderPage();
    expect(screen.getByText("notifications.markAllRead")).toBeInTheDocument();
  });

  it("shows refresh button", async () => {
    await renderPage();
    expect(screen.getByText("notifications.refresh")).toBeInTheDocument();
  });

  it("calls markAllAsRead on button click", async () => {
    const user = userEvent.setup();
    await renderPage();
    await user.click(screen.getByText("notifications.markAllRead"));
    await waitFor(() => {
      expect(mockMarkAllAsRead).toHaveBeenCalled();
    });
    expect(mockStoreMarkAllAsRead).toHaveBeenCalled();
  });

  it("fetches notifications on mount", async () => {
    await renderPage();
  });

  it("shows relative time", async () => {
    await renderPage();
    // 1 min ago should show minutesAgo
    expect(
      screen.getByText("notifications.timeAgo.minutesAgo"),
    ).toBeInTheDocument();
  });

  it("deletes notification on delete button click", async () => {
    const user = userEvent.setup();
    await renderPage();
    const deleteButtons = screen.getAllByTitle("common.delete");
    await user.click(deleteButtons[0]);
    // Confirm in the modal
    await waitFor(() => {
      expect(screen.getByTestId("confirm-modal")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Confirm"));
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith("n1");
    });
    expect(mockRemoveNotification).toHaveBeenCalledWith("n1");
  });
});
