import { usersService, type User } from '@/services/api';
import { clampPaginationParams } from '@/utils/security';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

/**
 * Hook for fetching users list.
 */
export function useUsers(params?: { skip?: number; limit?: number }) {
  const safeParams = clampPaginationParams(params);
  return useQuery({
    queryKey: ['users', safeParams],
    queryFn: () => usersService.list(safeParams),
  });
}

/**
 * Hook for fetching a single user.
 */
export function useUser(id: string) {
  return useQuery({
    queryKey: ['users', id],
    queryFn: () => usersService.get(id),
    enabled: !!id,
  });
}

/**
 * Hook for creating a user.
 */
export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Parameters<typeof usersService.create>[0]) =>
      usersService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

/**
 * Hook for updating a user.
 */
export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<User> }) =>
      usersService.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['users', id] });
    },
  });
}

/**
 * Hook for deleting a user.
 */
export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: usersService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
