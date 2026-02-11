/**
 * Unit tests for rolesService.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('./api', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

import { rolesService } from './rolesService';

describe('rolesService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should list roles', async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    const result = await rolesService.list({ skip: 0, limit: 10 });
    expect(mockGet).toHaveBeenCalledWith('/roles', { params: { skip: 0, limit: 10 } });
    expect(result.total).toBe(0);
  });

  it('should get a role', async () => {
    const role = { id: 'r1', name: 'Admin', permissions: ['*'] };
    mockGet.mockResolvedValueOnce({ data: role });
    const result = await rolesService.get('r1');
    expect(mockGet).toHaveBeenCalledWith('/roles/r1');
    expect(result.name).toBe('Admin');
  });

  it('should create a role', async () => {
    const data = { name: 'Editor', permissions: ['users:read'] };
    mockPost.mockResolvedValueOnce({ data: { id: 'r2', ...data, is_system: false } });
    const result = await rolesService.create(data);
    expect(mockPost).toHaveBeenCalledWith('/roles', data);
    expect(result.id).toBe('r2');
  });

  it('should update a role', async () => {
    mockPatch.mockResolvedValueOnce({ data: { id: 'r1', name: 'SuperAdmin' } });
    const result = await rolesService.update('r1', { name: 'SuperAdmin' });
    expect(mockPatch).toHaveBeenCalledWith('/roles/r1', { name: 'SuperAdmin' });
    expect(result.name).toBe('SuperAdmin');
  });

  it('should delete a role', async () => {
    mockDelete.mockResolvedValueOnce({ data: { message: 'Deleted' } });
    const result = await rolesService.delete('r1');
    expect(mockDelete).toHaveBeenCalledWith('/roles/r1');
    expect(result.message).toBe('Deleted');
  });

  it('should assign role to user', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'Assigned' } });
    const result = await rolesService.assignToUser({ user_id: 'u1', role_id: 'r1' });
    expect(mockPost).toHaveBeenCalledWith('/roles/assign', { user_id: 'u1', role_id: 'r1' });
    expect(result.message).toBe('Assigned');
  });

  it('should revoke role from user', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'Revoked' } });
    const result = await rolesService.revokeFromUser({ user_id: 'u1', role_id: 'r1' });
    expect(mockPost).toHaveBeenCalledWith('/roles/revoke', { user_id: 'u1', role_id: 'r1' });
    expect(result.message).toBe('Revoked');
  });

  it('should get user permissions', async () => {
    const perms = { user_id: 'u1', permissions: ['users:read'], roles: [] };
    mockGet.mockResolvedValueOnce({ data: perms });
    const result = await rolesService.getUserPermissions('u1');
    expect(mockGet).toHaveBeenCalledWith('/roles/users/u1/permissions');
    expect(result.permissions).toContain('users:read');
  });
});
