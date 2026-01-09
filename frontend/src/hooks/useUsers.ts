import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersService, type User } from '@/services/api';

/**
 * Hook for fetching users list.
 */
export function useUsers(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => usersService.list(params),
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
    mutationFn: (data: Partial<User> & { password: string }) =>
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
