/**
 * Unit tests for tenantsService.
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

import { tenantsService } from './tenantsService';

describe('tenantsService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should list tenants', async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0, skip: 0, limit: 20 } });
    const result = await tenantsService.list({ skip: 0, limit: 20 });
    expect(mockGet).toHaveBeenCalledWith('/tenants', { params: { skip: 0, limit: 20 } });
    expect(result.total).toBe(0);
  });

  it('should filter by is_active', async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    await tenantsService.list({ is_active: true });
    expect(mockGet).toHaveBeenCalledWith('/tenants', { params: { is_active: true } });
  });

  it('should get a tenant', async () => {
    const tenant = { id: 't1', name: 'Acme', slug: 'acme' };
    mockGet.mockResolvedValueOnce({ data: tenant });
    const result = await tenantsService.get('t1');
    expect(mockGet).toHaveBeenCalledWith('/tenants/t1');
    expect(result.name).toBe('Acme');
  });

  it('should create a tenant', async () => {
    const data = { name: 'NewCo', slug: 'newco' };
    mockPost.mockResolvedValueOnce({ data: { id: 't2', ...data } });
    const result = await tenantsService.create(data);
    expect(mockPost).toHaveBeenCalledWith('/tenants', data);
    expect(result.id).toBe('t2');
  });

  it('should update a tenant', async () => {
    mockPatch.mockResolvedValueOnce({ data: { id: 't1', name: 'Updated' } });
    const result = await tenantsService.update('t1', { name: 'Updated' });
    expect(mockPatch).toHaveBeenCalledWith('/tenants/t1', { name: 'Updated' });
    expect(result.name).toBe('Updated');
  });

  it('should delete a tenant', async () => {
    mockDelete.mockResolvedValueOnce({ data: { message: 'Deleted' } });
    const result = await tenantsService.delete('t1');
    expect(mockDelete).toHaveBeenCalledWith('/tenants/t1');
    expect(result.message).toBe('Deleted');
  });

  it('should activate a tenant', async () => {
    mockPost.mockResolvedValueOnce({ data: { id: 't1', is_active: true } });
    const result = await tenantsService.activate('t1');
    expect(mockPost).toHaveBeenCalledWith('/tenants/t1/activate');
    expect(result.is_active).toBe(true);
  });

  it('should deactivate a tenant', async () => {
    mockPost.mockResolvedValueOnce({ data: { id: 't1', is_active: false } });
    const result = await tenantsService.deactivate('t1');
    expect(mockPost).toHaveBeenCalledWith('/tenants/t1/deactivate');
    expect(result.is_active).toBe(false);
  });

  it('should verify a tenant', async () => {
    mockPost.mockResolvedValueOnce({ data: { id: 't1', is_verified: true } });
    const result = await tenantsService.verify('t1');
    expect(mockPost).toHaveBeenCalledWith('/tenants/t1/verify');
    expect(result.is_verified).toBe(true);
  });

  it('should update plan', async () => {
    mockPatch.mockResolvedValueOnce({ data: { id: 't1', plan: 'premium' } });
    const result = await tenantsService.updatePlan('t1', 'premium', '2027-01-01');
    expect(mockPatch).toHaveBeenCalledWith('/tenants/t1/plan', { plan: 'premium', plan_expires_at: '2027-01-01' });
    expect(result.plan).toBe('premium');
  });

  it('should update plan without expiry', async () => {
    mockPatch.mockResolvedValueOnce({ data: { id: 't1', plan: 'basic' } });
    await tenantsService.updatePlan('t1', 'basic');
    expect(mockPatch).toHaveBeenCalledWith('/tenants/t1/plan', { plan: 'basic', plan_expires_at: undefined });
  });
});
