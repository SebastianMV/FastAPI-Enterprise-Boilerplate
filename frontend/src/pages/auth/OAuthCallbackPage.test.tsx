import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import OAuthCallbackPage from "./OAuthCallbackPage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockSetTokens = vi.fn();
const mockFetchUser = vi.fn();

vi.mock("@/stores/authStore", () => ({
  useAuthStore: () => ({
    setTokens: mockSetTokens,
    fetchUser: mockFetchUser,
  }),
}));

const mockApiGet = vi.fn();
vi.mock("@/services/api", () => ({
  default: {
    get: (...args: unknown[]) => mockApiGet(...args),
  },
  OAUTH_PROVIDERS: [
    { id: "google", name: "Google", icon: "google", color: "#4285F4" },
    { id: "github", name: "GitHub", icon: "github", color: "#333" },
    { id: "microsoft", name: "Microsoft", icon: "microsoft", color: "#00A4EF" },
  ],
}));

// Save original location
const originalLocation = window.location;

function renderPage(search: string) {
  return render(
    <MemoryRouter initialEntries={[`/auth/oauth/callback${search}`]}>
      <OAuthCallbackPage />
    </MemoryRouter>,
  );
}

describe("OAuthCallbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockFetchUser.mockResolvedValue({});
    // Set up sessionStorage for CSRF state verification
    sessionStorage.setItem("oauth_state", "google_xyz");
    // Mock window.location.reload
    Object.defineProperty(window, "location", {
      value: { ...originalLocation, reload: vi.fn() },
      writable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    sessionStorage.clear();
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
    });
  });

  it("shows loading state initially", () => {
    mockApiGet.mockReturnValue(new Promise(() => {}));
    renderPage("?code=abc123&state=google_xyz");
    expect(screen.getByText("oauth.completingSignIn")).toBeInTheDocument();
    expect(screen.getByText("oauth.processing")).toBeInTheDocument();
  });

  it("shows error when error param is present", async () => {
    renderPage("?error=access_denied&error_description=User+denied+access");
    await waitFor(() => {
      expect(screen.getByText("oauth.authFailed")).toBeInTheDocument();
    });
    // error_description from URL is no longer rendered (F-03: prevents reflected phishing)
    expect(screen.getByText(/oauth.authFailedGeneric/)).toBeInTheDocument();
  });

  it("shows error when code is missing", async () => {
    renderPage("?state=google_xyz");
    await waitFor(() => {
      expect(screen.getByText("oauth.authFailed")).toBeInTheDocument();
    });
    expect(screen.getByText("oauth.invalidCallback")).toBeInTheDocument();
  });

  it("shows error when state is missing", async () => {
    renderPage("?code=abc123");
    await waitFor(() => {
      expect(screen.getByText("oauth.authFailed")).toBeInTheDocument();
    });
    expect(screen.getByText("oauth.invalidCallback")).toBeInTheDocument();
  });

  it("shows success for existing user", async () => {
    mockApiGet.mockResolvedValue({
      data: {
        access_token: "token",
        refresh_token: "refresh",
        token_type: "bearer",
        expires_in: 3600,
        user_id: "u1",
        is_new_user: false,
      },
    });
    renderPage("?code=abc123&state=google_xyz");
    await waitFor(() => {
      expect(screen.getByText("oauth.welcomeBack")).toBeInTheDocument();
    });
    expect(screen.getByText("oauth.signedIn")).toBeInTheDocument();
    expect(mockFetchUser).toHaveBeenCalled();
  });

  it("shows success for new user", async () => {
    sessionStorage.setItem("oauth_state", "github_xyz");
    mockApiGet.mockResolvedValue({
      data: {
        access_token: "token",
        refresh_token: "refresh",
        token_type: "bearer",
        expires_in: 3600,
        user_id: "u1",
        is_new_user: true,
      },
    });
    renderPage("?code=abc123&state=github_xyz");
    await waitFor(() => {
      expect(screen.getByText("oauth.welcome")).toBeInTheDocument();
    });
    expect(screen.getByText("oauth.accountCreated")).toBeInTheDocument();
  });

  it("calls API with correct provider and params", async () => {
    mockApiGet.mockResolvedValue({
      data: {
        access_token: "token",
        refresh_token: "refresh",
        token_type: "bearer",
        expires_in: 3600,
        user_id: "u1",
        is_new_user: false,
      },
    });
    renderPage("?code=abc123&state=google_xyz");
    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith("/auth/oauth/google/callback", {
        params: { code: "abc123", state: "google_xyz" },
        signal: expect.any(AbortSignal),
      });
    });
  });

  it("shows back to login on error", async () => {
    renderPage("?error=access_denied");
    await waitFor(() => {
      expect(screen.getByText("oauth.backToLogin")).toBeInTheDocument();
    });
  });

  it("shows error message on error param", async () => {
    renderPage("?error=access_denied");
    await waitFor(() => {
      expect(screen.getByText(/oauth.authFailedGeneric/)).toBeInTheDocument();
    });
  });

  it("shows error when API call fails", async () => {
    mockApiGet.mockRejectedValue(new Error("Network error"));
    renderPage("?code=abc123&state=google_xyz");
    await waitFor(() => {
      expect(screen.getByText("oauth.authFailed")).toBeInTheDocument();
    });
    // Generic error message shown instead of raw error.message (security: no info leak)
    expect(screen.getByText("oauth.authFailedGeneric")).toBeInTheDocument();
  });
});
