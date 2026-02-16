/**
 * Unit tests for DashboardPage component.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPage from "./DashboardPage";

// Mock auth store
vi.mock("@/stores/authStore", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock store selector
  useAuthStore: (selector: (s: any) => any) =>
    selector({
      user: {
        id: "1",
        first_name: "Admin",
        last_name: "User",
        is_superuser: true,
      },
    }),
}));

// Mock dashboard service
const mockGetStats = vi.fn();
const mockGetActivity = vi.fn();
const mockGetHealth = vi.fn();

vi.mock("@/services/api", () => ({
  dashboardService: {
    getStats: () => mockGetStats(),
    getActivity: (...a: unknown[]) => mockGetActivity(...a),
    getHealth: () => mockGetHealth(),
  },
}));

const sampleStats = {
  total_users: 100,
  active_users: 80,
  inactive_users: 20,
  users_created_last_7_days: 5,
  users_created_last_30_days: 15,
  stats: [
    { name: "Total Users", value: 100, change: "+5%", change_type: "positive" },
    { name: "Active Users", value: 80, change: "+3%", change_type: "positive" },
    { name: "API Keys", value: 12, change: "0%", change_type: "neutral" },
    { name: "Roles", value: 4, change: "-1%", change_type: "negative" },
  ],
};

const sampleActivity = {
  total: 2,
  items: [
    {
      id: "a1",
      action: "user_registered",
      description: "User john@test.com registered",
      user_email: "john@test.com",
      timestamp: new Date().toISOString(),
    },
    {
      id: "a2",
      action: "api_key_created",
      description: "API key created",
      user_email: "admin@test.com",
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
  ],
};

const sampleHealth = {
  database_status: "healthy",
  cache_status: "healthy",
  avg_response_time_ms: 42,
  active_sessions: 5,
  uptime_percentage: 99.9,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetStats.mockResolvedValue(sampleStats);
    mockGetActivity.mockResolvedValue(sampleActivity);
    mockGetHealth.mockResolvedValue(sampleHealth);
  });

  it("should show loading state initially", () => {
    // Never resolving promises
    mockGetStats.mockReturnValue(new Promise(() => {}));
    mockGetActivity.mockReturnValue(new Promise(() => {}));
    mockGetHealth.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("dashboard.loadingDashboard")).toBeInTheDocument();
  });

  it("should render welcome message with user name", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.welcome")).toBeInTheDocument();
    });
  });

  it("should render stat cards after loading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.statTotalUsers")).toBeInTheDocument();
      expect(screen.getByText("100")).toBeInTheDocument();
      expect(screen.getByText("+5%")).toBeInTheDocument();
    });
  });

  it("should render recent activity", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.recentActivity")).toBeInTheDocument();
      expect(
        screen.getByText("User john@test.com registered"),
      ).toBeInTheDocument();
    });
  });

  it("should render quick actions", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.quickActions")).toBeInTheDocument();
      expect(screen.getByText("dashboard.addUser")).toBeInTheDocument();
      // 'API Keys' appears in both stats and quick actions
      expect(
        screen.getAllByText("dashboard.apiKeys").length,
      ).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("dashboard.security")).toBeInTheDocument();
    });
  });

  it("should render system health banner", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(
          (text) => text.includes("42") && text.includes("common.ms"),
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("99.9%")).toBeInTheDocument();
    });
  });

  it("should show error state on fetch failure", async () => {
    mockGetStats.mockRejectedValue(new Error("Network error"));
    mockGetActivity.mockRejectedValue(new Error("Network error"));
    mockGetHealth.mockRejectedValue(new Error("Network error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.failedToLoad")).toBeInTheDocument();
    });
  });

  it("should have refresh button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.refreshData")).toBeInTheDocument();
    });
  });

  it("should call fetchDashboardData on refresh click", async () => {
    renderPage();
    await waitFor(() => screen.getByText("dashboard.refreshData"));
    mockGetStats.mockResolvedValue(sampleStats);
    fireEvent.click(screen.getByText("dashboard.refreshData"));
    await waitFor(() => {
      // Stats called initially + refresh
      expect(mockGetStats).toHaveBeenCalledTimes(2);
    });
  });

  it("should render user overview stats", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.userOverview")).toBeInTheDocument();
      expect(
        screen.getByText("dashboard.newUsersLast7Days"),
      ).toBeInTheDocument();
    });
  });
});
