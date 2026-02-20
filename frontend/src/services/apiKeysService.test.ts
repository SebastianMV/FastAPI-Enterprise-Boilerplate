import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockApi } = vi.hoisted(() => ({
  mockApi: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("./api", () => ({
  default: mockApi,
}));

import { apiKeysService } from "./apiKeysService";

describe("apiKeysService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list calls /api-keys with include_revoked=false by default", async () => {
    const response = {
      items: [
        {
          id: "1",
          name: "Primary",
          prefix: "ak_test",
          scopes: ["read:users"],
          is_active: true,
          expires_at: null,
          last_used_at: null,
          usage_count: 0,
          created_at: "2026-02-18T00:00:00Z",
        },
      ],
      total: 1,
    };
    mockApi.get.mockResolvedValueOnce({ data: response });

    const result = await apiKeysService.list();

    expect(mockApi.get).toHaveBeenCalledWith("/api-keys", {
      params: { include_revoked: false },
    });
    expect(result).toEqual(response);
  });

  it("list supports includeRevoked=true", async () => {
    mockApi.get.mockResolvedValueOnce({ data: { items: [], total: 0 } });

    await apiKeysService.list(true);

    expect(mockApi.get).toHaveBeenCalledWith("/api-keys", {
      params: { include_revoked: true },
    });
  });

  it("create sends sanitized payload and returns created key", async () => {
    const input = {
      name: "Backend integration key",
      scopes: ["read:users", "write:users"],
      expires_in_days: 30,
      extra: "should-not-be-sent",
    } as unknown as {
      name: string;
      scopes: string[];
      expires_in_days: number | null;
    };

    const created = {
      id: "key-1",
      name: "Backend integration key",
      prefix: "ak_123",
      key: "secret-value",
      scopes: ["read:users", "write:users"],
      expires_at: null,
      created_at: "2026-02-18T00:00:00Z",
    };

    mockApi.post.mockResolvedValueOnce({ data: created });

    const result = await apiKeysService.create(input);

    expect(mockApi.post).toHaveBeenCalledWith("/api-keys", {
      name: "Backend integration key",
      scopes: ["read:users", "write:users"],
      expires_in_days: 30,
    });
    expect(result).toEqual(created);
  });

  it("revoke encodes id in URL path", async () => {
    const id = "id/with spaces?and=query";
    mockApi.delete.mockResolvedValueOnce({ data: { message: "revoked" } });

    const result = await apiKeysService.revoke(id);

    expect(mockApi.delete).toHaveBeenCalledWith(
      "/api-keys/id%2Fwith%20spaces%3Fand%3Dquery",
    );
    expect(result).toEqual({ message: "revoked" });
  });
});
