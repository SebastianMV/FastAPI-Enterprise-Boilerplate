import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

interface MockAxiosInstance {
  (...args: unknown[]): Promise<unknown>;
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  patch: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  interceptors: {
    request: { use: ReturnType<typeof vi.fn> };
    response: { use: ReturnType<typeof vi.fn> };
  };
}

const mockInstances: MockAxiosInstance[] = [];

const createMockAxiosInstance = (): MockAxiosInstance => {
  const instance = vi.fn() as unknown as MockAxiosInstance;
  instance.get = vi.fn();
  instance.post = vi.fn();
  instance.patch = vi.fn();
  instance.delete = vi.fn();
  instance.put = vi.fn();
  instance.interceptors = {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  };
  return instance;
};

vi.mock("axios", () => {
  const create = vi.fn(() => {
    const instance = createMockAxiosInstance();
    mockInstances.push(instance);
    return instance;
  });

  return {
    default: {
      create,
      post: vi.fn(),
    },
  };
});

const getPrimaryApi = (): MockAxiosInstance => {
  const first = mockInstances[0];
  if (!first) {
    throw new Error("Primary axios instance not initialized");
  }
  return first;
};

describe("api service", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockInstances.length = 0;
    document.cookie = "";
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports service objects from api index", async () => {
    const mod = await import("./api");

    expect(mod.authService).toBeDefined();
    expect(mod.usersService).toBeDefined();
    expect(mod.default).toBeDefined();
  });

  it("registers request and response interceptors", async () => {
    await import("./api");
    const apiInstance = getPrimaryApi();

    expect(apiInstance.interceptors.request.use).toHaveBeenCalledTimes(1);
    expect(apiInstance.interceptors.response.use).toHaveBeenCalledTimes(1);
  });

  it("adds csrf header on state-changing methods", async () => {
    await import("./api");
    const apiInstance = getPrimaryApi();

    const requestInterceptor = apiInstance.interceptors.request.use.mock
      .calls[0]?.[0] as
      | ((cfg: { method?: string; headers: Record<string, string> }) => {
          method?: string;
          headers: Record<string, string>;
        })
      | undefined;

    expect(requestInterceptor).toBeDefined();
    document.cookie = "csrf_token=test-token";

    const config = { method: "post", headers: {} as Record<string, string> };
    const result = requestInterceptor?.(config);

    expect(result?.headers["X-CSRF-Token"]).toBe("test-token");
  });

  it("does not add csrf header on get requests", async () => {
    await import("./api");
    const apiInstance = getPrimaryApi();

    const requestInterceptor = apiInstance.interceptors.request.use.mock
      .calls[0]?.[0] as
      | ((cfg: { method?: string; headers: Record<string, string> }) => {
          method?: string;
          headers: Record<string, string>;
        })
      | undefined;

    document.cookie = "csrf_token=test-token";
    const config = { method: "get", headers: {} as Record<string, string> };
    const result = requestInterceptor?.(config);

    expect(result?.headers["X-CSRF-Token"]).toBeUndefined();
  });

  it("retries original request when 401 refresh succeeds", async () => {
    const mod = await import("./api");
    const apiInstance = getPrimaryApi();
    const axiosCreate = (
      axios as unknown as { create: ReturnType<typeof vi.fn> }
    ).create;

    const responseInterceptor = apiInstance.interceptors.response.use.mock
      .calls[0]?.[1] as
      | ((error: {
          config: { _retry?: boolean };
          response?: { status?: number };
        }) => Promise<unknown>)
      | undefined;

    expect(responseInterceptor).toBeDefined();

    const refreshInstance = createMockAxiosInstance();
    refreshInstance.post.mockResolvedValueOnce({
      data: { access_token: "new-token" },
    });
    axiosCreate.mockImplementationOnce(() => refreshInstance);

    apiInstance.mockResolvedValueOnce({ data: { ok: true } });

    const error = {
      config: { _retry: false },
      response: { status: 401 },
    };

    const result = await responseInterceptor?.(error);

    expect(axiosCreate).toHaveBeenCalled();
    expect(refreshInstance.post).toHaveBeenCalledWith(
      "/auth/refresh",
      {},
      {
        headers: expect.any(Object),
      },
    );
    expect(apiInstance).toHaveBeenCalledWith(error.config);
    expect(result).toEqual({ data: { ok: true } });
    expect(mod.AUTH_LOGOUT_EVENT).toBe("auth:logout");
  });

  it("emits logout event when refresh fails", async () => {
    const mod = await import("./api");
    const apiInstance = getPrimaryApi();
    const axiosCreate = (
      axios as unknown as { create: ReturnType<typeof vi.fn> }
    ).create;

    const responseInterceptor = apiInstance.interceptors.response.use.mock
      .calls[0]?.[1] as
      | ((error: {
          config: { _retry?: boolean };
          response?: { status?: number };
        }) => Promise<unknown>)
      | undefined;

    const handler = vi.fn();
    window.addEventListener(mod.AUTH_LOGOUT_EVENT, handler);

    const refreshInstance = createMockAxiosInstance();
    refreshInstance.post.mockRejectedValueOnce(new Error("refresh failed"));
    axiosCreate.mockImplementationOnce(() => refreshInstance);

    await expect(
      responseInterceptor?.({
        config: { _retry: false },
        response: { status: 401 },
      }),
    ).rejects.toThrow("refresh failed");

    expect(handler).toHaveBeenCalledTimes(1);
    window.removeEventListener(mod.AUTH_LOGOUT_EVENT, handler);
  });

  it("authService login calls expected endpoint", async () => {
    const mod = await import("./api");
    const apiInstance = getPrimaryApi();

    const payload = {
      access_token: "token",
      token_type: "bearer",
      expires_in: 3600,
      user: {
        id: "1",
        email: "u@example.com",
        first_name: "U",
        last_name: "S",
        is_active: true,
        is_superuser: false,
        email_verified: true,
        created_at: "2026-02-18T00:00:00Z",
      },
    };

    apiInstance.post.mockResolvedValueOnce({ data: payload });

    const result = await mod.authService.login({
      email: "u@example.com",
      password: "Secret123!",
    });

    expect(apiInstance.post).toHaveBeenCalledWith("/auth/login", {
      email: "u@example.com",
      password: "Secret123!",
    });
    expect(result).toEqual(payload);
  });

  it("usersService list uses default pagination values", async () => {
    const mod = await import("./api");
    const apiInstance = getPrimaryApi();

    apiInstance.get.mockResolvedValueOnce({
      data: { items: [], total: 0, skip: 0, limit: 20 },
    });

    await mod.usersService.list();

    expect(apiInstance.get).toHaveBeenCalledWith("/users", {
      params: { skip: 0, limit: 20 },
    });
  });
});
