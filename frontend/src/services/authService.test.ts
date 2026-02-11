/**
 * Unit tests for authService.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('./api', () => {
  const instance = {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  };
  return { default: instance };
});

import { authService } from './authService';

describe('authService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('login', () => {
    it('should POST /auth/login with credentials', async () => {
      const mockResponse = {
        data: {
          access_token: 'token-123',
          refresh_token: 'refresh-456',
          token_type: 'bearer',
          expires_in: 3600,
          user: { id: '1', email: 'a@b.com' },
        },
      };
      mockPost.mockResolvedValueOnce(mockResponse);

      const result = await authService.login({ email: 'a@b.com', password: 'pass' });

      expect(mockPost).toHaveBeenCalledWith('/auth/login', { email: 'a@b.com', password: 'pass' });
      expect(result.access_token).toBe('token-123');
      expect(result.user.email).toBe('a@b.com');
    });

    it('should pass mfa_code when provided', async () => {
      mockPost.mockResolvedValueOnce({ data: { access_token: 't', user: {} } });

      await authService.login({ email: 'a@b.com', password: 'p', mfa_code: '123456' });

      expect(mockPost).toHaveBeenCalledWith('/auth/login', {
        email: 'a@b.com',
        password: 'p',
        mfa_code: '123456',
      });
    });

    it('should propagate API errors', async () => {
      mockPost.mockRejectedValueOnce(new Error('401 Unauthorized'));

      await expect(authService.login({ email: 'a@b.com', password: 'wrong' }))
        .rejects.toThrow('401 Unauthorized');
    });
  });

  describe('logout', () => {
    it('should POST /auth/logout', async () => {
      mockPost.mockResolvedValueOnce({ data: undefined });

      await authService.logout();

      expect(mockPost).toHaveBeenCalledWith('/auth/logout');
    });
  });

  describe('refresh', () => {
    it('should POST /auth/refresh without arguments (cookies handle refresh token)', async () => {
      mockPost.mockResolvedValueOnce({
        data: { access_token: 'new-token', token_type: 'bearer', expires_in: 3600 },
      });

      const result = await authService.refresh();

      expect(mockPost).toHaveBeenCalledWith('/auth/refresh', {});
      expect(result.access_token).toBe('new-token');
    });
  });

  describe('me', () => {
    it('should GET /auth/me', async () => {
      const user = { id: '1', email: 'a@b.com', first_name: 'Test' };
      mockGet.mockResolvedValueOnce({ data: user });

      const result = await authService.me();

      expect(mockGet).toHaveBeenCalledWith('/auth/me');
      expect(result).toEqual(user);
    });
  });
});
