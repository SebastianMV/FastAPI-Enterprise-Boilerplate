/**
 * Unit tests for auditLogsService.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();

vi.mock("./api", () => ({
  default: { get: (...args: unknown[]) => mockGet(...args) },
}));

import { auditLogsService } from "./auditLogsService";

describe("auditLogsService", () => {
  beforeEach(() => vi.clearAllMocks());

  it("should list audit logs", async () => {
    mockGet.mockResolvedValueOnce({
      data: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
    });
    const result = await auditLogsService.list({
      action: "login",
      page_size: 20,
    });
    expect(mockGet).toHaveBeenCalledWith("/audit-logs", {
      params: { action: "login", page: 1, page_size: 20 },
    });
    expect(result.total).toBe(0);
  });

  it("should list without filters", async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    await auditLogsService.list();
    expect(mockGet).toHaveBeenCalledWith("/audit-logs", {
      params: { page: 1, page_size: 20 },
    });
  });

  it("should get a single audit log", async () => {
    const log = { id: "a1", action: "login", resource_type: "user" };
    mockGet.mockResolvedValueOnce({ data: log });
    const result = await auditLogsService.get("a1");
    expect(mockGet).toHaveBeenCalledWith("/audit-logs/a1");
    expect(result.action).toBe("login");
  });

  it("should get my activity", async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    await auditLogsService.getMyActivity({ page_size: 5 });
    expect(mockGet).toHaveBeenCalledWith("/audit-logs/my-activity", {
      params: { page: 1, page_size: 5 },
    });
  });

  it("should get recent logins", async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    await auditLogsService.getRecentLogins(10, true);
    expect(mockGet).toHaveBeenCalledWith("/audit-logs/recent-logins", {
      params: { page_size: 10, include_failed: true },
    });
  });

  it("should get resource history", async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    await auditLogsService.getResourceHistory("user", "u1", { page: 1 });
    expect(mockGet).toHaveBeenCalledWith("/audit-logs/resource/user/u1", {
      params: { page: 1, page_size: 20 },
    });
  });

  it("should get actions list", async () => {
    mockGet.mockResolvedValueOnce({ data: ["login", "logout", "create"] });
    const result = await auditLogsService.getActions();
    expect(mockGet).toHaveBeenCalledWith("/audit-logs/actions/list");
    expect(result).toContain("login");
  });

  it("should get resource types list", async () => {
    mockGet.mockResolvedValueOnce({ data: ["user", "role", "tenant"] });
    const result = await auditLogsService.getResourceTypes();
    expect(mockGet).toHaveBeenCalledWith("/audit-logs/resource-types/list");
    expect(result).toContain("user");
  });
});
