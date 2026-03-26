/**
 * Unit tests for usersService.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock("./api", () => {
  const instance = {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  };
  return { default: instance };
});

import { usersService } from "./usersService";

describe("usersService", () => {
  beforeEach(() => vi.clearAllMocks());

  describe("list", () => {
    it("should GET /users with default params", async () => {
      mockGet.mockResolvedValueOnce({
        data: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
      });
      const result = await usersService.list();
      expect(mockGet).toHaveBeenCalledWith("/users", {
        params: { page: 1, page_size: 20 },
      });
      expect(result.items).toEqual([]);
    });

    it("should pass pagination params", async () => {
      mockGet.mockResolvedValueOnce({
        data: { items: [], total: 0, page: 3, page_size: 5, pages: 0 },
      });
      await usersService.list({ page: 3, page_size: 5 });
      expect(mockGet).toHaveBeenCalledWith("/users", {
        params: { page: 3, page_size: 5 },
      });
    });
  });

  describe("get", () => {
    it("should GET /users/:id", async () => {
      const user = { id: "u1", email: "a@b.com" };
      mockGet.mockResolvedValueOnce({ data: user });
      const result = await usersService.get("u1");
      expect(mockGet).toHaveBeenCalledWith("/users/u1");
      expect(result).toEqual(user);
    });
  });

  describe("create", () => {
    it("should POST /users", async () => {
      const newUser = {
        email: "new@b.com",
        password: "Pass123!",
        first_name: "New",
        last_name: "User",
      };
      mockPost.mockResolvedValueOnce({ data: { id: "u2", ...newUser } });
      const result = await usersService.create(newUser);
      expect(mockPost).toHaveBeenCalledWith("/users", newUser);
      expect(result.id).toBe("u2");
    });
  });

  describe("update", () => {
    it("should PATCH /users/:id", async () => {
      mockPatch.mockResolvedValueOnce({
        data: { id: "u1", first_name: "Updated" },
      });
      const result = await usersService.update("u1", { first_name: "Updated" });
      expect(mockPatch).toHaveBeenCalledWith("/users/u1", {
        first_name: "Updated",
      });
      expect(result.first_name).toBe("Updated");
    });
  });

  describe("updateMe", () => {
    it("should PATCH /users/me", async () => {
      mockPatch.mockResolvedValueOnce({ data: { id: "me", first_name: "Me" } });
      const result = await usersService.updateMe({ first_name: "Me" });
      expect(mockPatch).toHaveBeenCalledWith("/users/me", { first_name: "Me" });
      expect(result.first_name).toBe("Me");
    });
  });

  describe("uploadAvatar", () => {
    it("should POST /users/me/avatar with FormData", async () => {
      const file = new File(["img"], "avatar.png", { type: "image/png" });
      mockPost.mockResolvedValueOnce({
        data: { id: "me", avatar_url: "/avatars/me.png" },
      });
      const result = await usersService.uploadAvatar(file);
      expect(mockPost).toHaveBeenCalledWith(
        "/users/me/avatar",
        expect.any(FormData),
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );
      expect(result.avatar_url).toBe("/avatars/me.png");
    });
  });

  describe("deleteAvatar", () => {
    it("should DELETE /users/me/avatar", async () => {
      mockDelete.mockResolvedValueOnce({ data: { message: "Avatar deleted" } });
      const result = await usersService.deleteAvatar();
      expect(mockDelete).toHaveBeenCalledWith("/users/me/avatar");
      expect(result.message).toBe("Avatar deleted");
    });
  });

  describe("delete", () => {
    it("should DELETE /users/:id", async () => {
      mockDelete.mockResolvedValueOnce({ data: undefined });
      await usersService.delete("u1");
      expect(mockDelete).toHaveBeenCalledWith("/users/u1");
    });
  });
});
