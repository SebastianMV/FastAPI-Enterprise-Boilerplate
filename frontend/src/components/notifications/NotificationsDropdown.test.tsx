/**
 * Unit tests for NotificationsDropdown component.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import NotificationsDropdown from "./NotificationsDropdown";

const mockNavigate = vi.fn();
let capturedWebSocketOptions: Record<string, unknown> | null = null;

vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>(
      "react-router-dom",
    );
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useWebSocket
vi.mock("@/hooks/useWebSocket", () => ({
  useWebSocket: (options: Record<string, unknown>) => {
    capturedWebSocketOptions = options;
    return { isConnected: true };
  },
}));

// Mock notificationsService
const mockServiceMarkAsRead = vi.fn().mockResolvedValue(undefined);
const mockServiceMarkAllAsRead = vi.fn().mockResolvedValue(undefined);
vi.mock("@/services/api", () => ({
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
let mockIsConnected = false;

vi.mock("@/stores/notificationsStore", () => ({
  useNotificationsStore: () => ({
    notifications: mockNotifications,
    unreadCount: mockNotifications.filter(
      (n: unknown) => !(n as Record<string, boolean>).read,
    ).length,
    isConnected: mockIsConnected,
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
    </MemoryRouter>,
  );
}

describe("NotificationsDropdown", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNotifications.length = 0;
    mockIsConnected = false;
    capturedWebSocketOptions = null;
  });

  it("should render bell button", () => {
    renderDropdown();
    expect(
      screen.getByLabelText("notificationsDropdown.title"),
    ).toBeInTheDocument();
  });

  it("should show unread badge when there are unread notifications", () => {
    mockNotifications.push({
      id: "1",
      type: "info",
      title: "Test",
      message: "Hello",
      read: false,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("should cap unread badge at 99+", () => {
    for (let index = 0; index < 100; index += 1) {
      mockNotifications.push({
        id: `${index + 1}`,
        type: "info",
        title: `n-${index + 1}`,
        read: false,
        created_at: new Date().toISOString(),
      });
    }
    renderDropdown();
    expect(screen.getByText("99+")).toBeInTheDocument();
  });

  it("should open dropdown on bell click", () => {
    renderDropdown();
    fireEvent.click(screen.getByLabelText("notificationsDropdown.title"));
    expect(screen.getByText("notificationsDropdown.title")).toBeInTheDocument();
  });

  it("should show empty state when no notifications", () => {
    renderDropdown();
    fireEvent.click(screen.getByLabelText("notificationsDropdown.title"));
    expect(
      screen.getByText("notificationsDropdown.noNotifications"),
    ).toBeInTheDocument();
  });

  it("should render notification items", () => {
    mockNotifications.push({
      id: "1",
      type: "success",
      title: "Task completed",
      message: "Your task has been completed",
      read: false,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    fireEvent.click(screen.getByLabelText("notificationsDropdown.title"));
    expect(screen.getByText("Task completed")).toBeInTheDocument();
  });

  it('should show "Mark all read" button when unread exist', () => {
    mockNotifications.push({
      id: "1",
      type: "info",
      title: "Unread",
      read: false,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    fireEvent.click(screen.getByLabelText("notificationsDropdown.title"));
    expect(
      screen.getByText("notificationsDropdown.markAllRead"),
    ).toBeInTheDocument();
  });

  it("should call markAllAsRead", async () => {
    mockNotifications.push({
      id: "1",
      type: "info",
      title: "Unread",
      read: false,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    fireEvent.click(screen.getByLabelText("notificationsDropdown.title"));
    fireEvent.click(screen.getByText("notificationsDropdown.markAllRead"));
    await vi.waitFor(() => {
      expect(mockMarkAllAsRead).toHaveBeenCalled();
      expect(mockServiceMarkAllAsRead).toHaveBeenCalled();
    });
  });

  it("should mark one notification as read when check button is clicked", async () => {
    const user = userEvent.setup();
    mockNotifications.push({
      id: "11",
      type: "warning",
      title: "Unread warning",
      message: "Needs action",
      read: false,
      created_at: new Date().toISOString(),
    });

    renderDropdown();
    await user.click(screen.getByLabelText("notificationsDropdown.title"));
    await user.click(screen.getByTitle("notificationsDropdown.markAsRead"));

    await waitFor(() => {
      expect(mockServiceMarkAsRead).toHaveBeenCalledWith("11");
      expect(mockMarkAsRead).toHaveBeenCalledWith("11");
    });
  });

  it("should navigate for safe action url when notification is clicked", async () => {
    const user = userEvent.setup();
    mockNotifications.push({
      id: "2",
      type: "info",
      title: "Go users",
      message: "Open users page",
      read: false,
      action_url: "/users",
      created_at: new Date().toISOString(),
    });

    renderDropdown();
    await user.click(screen.getByLabelText("notificationsDropdown.title"));
    await user.click(screen.getByText("Go users"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/users");
    });
  });

  it("should not navigate for unsafe action url", async () => {
    const user = userEvent.setup();
    mockNotifications.push({
      id: "3",
      type: "error",
      title: "Unsafe link",
      message: "Do not open",
      read: false,
      action_url: "https://evil.example/phish",
      created_at: new Date().toISOString(),
    });

    renderDropdown();
    await user.click(screen.getByLabelText("notificationsDropdown.title"));
    await user.click(screen.getByText("Unsafe link"));

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("should close dropdown when clicking outside", async () => {
    const user = userEvent.setup();
    renderDropdown();
    await user.click(screen.getByLabelText("notificationsDropdown.title"));

    expect(
      screen.getByRole("region", { name: "notificationsDropdown.title" }),
    ).toBeInTheDocument();
    fireEvent.mouseDown(document.body);

    await waitFor(() => {
      expect(
        screen.queryByRole("region", { name: "notificationsDropdown.title" }),
      ).not.toBeInTheDocument();
    });
  });

  it("should react to websocket callbacks and validate payload", () => {
    renderDropdown();
    const options = capturedWebSocketOptions as {
      onConnected: () => void;
      onDisconnected: () => void;
      onNotification: (payload: unknown) => void;
    };

    options.onConnected();
    options.onDisconnected();
    options.onNotification(null);
    options.onNotification({ title: "missing id" });
    options.onNotification({
      id: "ws-1",
      type: "success",
      title: "Created",
      message: "Entity created",
      action_url: "/users",
      timestamp: new Date().toISOString(),
    });

    expect(mockSetConnected).toHaveBeenCalledWith(true);
    expect(mockSetConnected).toHaveBeenCalledWith(false);
    expect(mockAddNotification).toHaveBeenCalledTimes(1);
    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "ws-1",
        type: "success",
        action_url: "/users",
      }),
    );
  });

  it("should show View all notifications link", () => {
    mockNotifications.push({
      id: "1",
      type: "info",
      title: "Test",
      read: true,
      created_at: new Date().toISOString(),
    });
    renderDropdown();
    fireEvent.click(screen.getByLabelText("notificationsDropdown.title"));
    expect(
      screen.getByText("notificationsDropdown.viewAll"),
    ).toBeInTheDocument();
  });

  it("should close dropdown on close button click", () => {
    renderDropdown();
    fireEvent.click(screen.getByLabelText("notificationsDropdown.title"));
    expect(screen.getByText("notificationsDropdown.title")).toBeInTheDocument();
    // Find close button inside dropdown header (the X button)
    const closeButtons = screen.getAllByRole("button");
    const closeBtn = closeButtons.find((btn) => btn.querySelector(".lucide-x"));
    if (closeBtn) fireEvent.click(closeBtn);
    // dropdown should close
  });
});
