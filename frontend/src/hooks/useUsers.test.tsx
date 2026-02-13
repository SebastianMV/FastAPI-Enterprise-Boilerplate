/**
 * Tests for useUsers hooks.
 */
import { usersService } from '@/services/api';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCreateUser, useDeleteUser, useUpdateUser, useUser, useUsers } from './useUsers';

// Mock the users service
vi.mock('@/services/api', () => ({
  usersService: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockUsersService = usersService as unknown as {
  list: ReturnType<typeof vi.fn>;
  get: ReturnType<typeof vi.fn>;
  create: ReturnType<typeof vi.fn>;
  update: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

// Create a wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useUsers hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useUsers', () => {
    it('should fetch users list', async () => {
      const mockUsers = {
        items: [
          { id: '1', email: 'user1@example.com', full_name: 'User 1' },
          { id: '2', email: 'user2@example.com', full_name: 'User 2' },
        ],
        total: 2,
      };
      mockUsersService.list.mockResolvedValue(mockUsers);

      const { result } = renderHook(() => useUsers(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockUsers);
      expect(mockUsersService.list).toHaveBeenCalledWith({ skip: 0, limit: 20 });
    });

    it('should pass pagination params to list', async () => {
      mockUsersService.list.mockResolvedValue({ items: [], total: 0 });

      const { result } = renderHook(() => useUsers({ skip: 10, limit: 20 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockUsersService.list).toHaveBeenCalledWith({ skip: 10, limit: 20 });
    });

    it('should handle fetch error', async () => {
      mockUsersService.list.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useUsers(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
    });
  });

  describe('useUser', () => {
    it('should fetch single user by id', async () => {
      const mockUser = { id: '1', email: 'user@example.com', full_name: 'Test User' };
      mockUsersService.get.mockResolvedValue(mockUser);

      const { result } = renderHook(() => useUser('1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockUser);
      expect(mockUsersService.get).toHaveBeenCalledWith('1');
    });

    it('should not fetch when id is empty', async () => {
      const { result } = renderHook(() => useUser(''), {
        wrapper: createWrapper(),
      });

      // Query should not be enabled
      expect(result.current.fetchStatus).toBe('idle');
      expect(mockUsersService.get).not.toHaveBeenCalled();
    });
  });

  describe('useCreateUser', () => {
    it('should create a new user', async () => {
      const newUser = { email: 'new@example.com', password: 'password123', first_name: 'New', last_name: 'User' };
      const createdUser = { id: '3', ...newUser };
      mockUsersService.create.mockResolvedValue(createdUser);

      const { result } = renderHook(() => useCreateUser(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(newUser);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockUsersService.create).toHaveBeenCalledWith(newUser);
    });

    it('should handle creation error', async () => {
      mockUsersService.create.mockRejectedValue(new Error('Email already exists'));

      const { result } = renderHook(() => useCreateUser(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ email: 'existing@example.com', password: 'pass', first_name: 'Existing', last_name: 'User' });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useUpdateUser', () => {
    it('should update an existing user', async () => {
      const updateData = { first_name: 'Updated Name' };
      const updatedUser = { id: '1', email: 'user@example.com', ...updateData };
      mockUsersService.update.mockResolvedValue(updatedUser);

      const { result } = renderHook(() => useUpdateUser(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ id: '1', data: updateData });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockUsersService.update).toHaveBeenCalledWith('1', updateData);
    });
  });

  describe('useDeleteUser', () => {
    it('should delete a user', async () => {
      mockUsersService.delete.mockResolvedValue(undefined);

      const { result } = renderHook(() => useDeleteUser(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('1');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // React Query passes additional args, so we check the first argument
      expect(mockUsersService.delete).toHaveBeenCalled();
      expect(mockUsersService.delete.mock.calls[0][0]).toBe('1');
    });
  });
});
