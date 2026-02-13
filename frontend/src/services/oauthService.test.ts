/**
 * Unit tests for oauthService.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockGet = vi.fn();
const mockDelete = vi.fn();

vi.mock('./api', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

import { OAUTH_PROVIDERS, oauthService } from './oauthService';

describe('oauthService', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('OAUTH_PROVIDERS', () => {
    it('should define Google, GitHub, Microsoft providers', () => {
      expect(OAUTH_PROVIDERS).toHaveLength(3);
      expect(OAUTH_PROVIDERS.map(p => p.id)).toEqual(['google', 'github', 'microsoft']);
    });

    it('should have required fields on each provider', () => {
      for (const p of OAUTH_PROVIDERS) {
        expect(p).toHaveProperty('id');
        expect(p).toHaveProperty('name');
        expect(p).toHaveProperty('icon');
        expect(p).toHaveProperty('color');
      }
    });
  });

  describe('getAuthorizationUrl', () => {
    it('should GET /auth/oauth/:provider/authorize', async () => {
      const data = { authorization_url: 'https://google.com/auth', state: 'xyz' };
      mockGet.mockResolvedValueOnce({ data });
      const result = await oauthService.getAuthorizationUrl('google');
      expect(mockGet).toHaveBeenCalledWith('/auth/oauth/google/authorize');
      expect(result.authorization_url).toBe('https://google.com/auth');
    });
  });

  describe('redirectToProvider', () => {
    it('should redirect to authorization URL', async () => {
      const data = { authorization_url: 'https://github.com/auth', state: 'abc' };
      mockGet.mockResolvedValueOnce({ data });

      // Replace window.location to capture href assignment
      const originalLocation = window.location;
      const mockLocation = { ...originalLocation, href: '' } as Location;
      Object.defineProperty(window, 'location', { value: mockLocation, writable: true });

      await oauthService.redirectToProvider('github');

      expect(mockLocation.href).toBe('https://github.com/auth');
      Object.defineProperty(window, 'location', { value: originalLocation, writable: true });
    });
  });

  describe('getConnections', () => {
    it('should GET /auth/oauth/connections', async () => {
      const connections = [{ id: 'c1', provider: 'google', provider_email: 'a@gmail.com' }];
      mockGet.mockResolvedValueOnce({ data: connections });
      const result = await oauthService.getConnections();
      expect(mockGet).toHaveBeenCalledWith('/auth/oauth/connections');
      expect(result).toEqual(connections);
    });
  });

  describe('disconnect', () => {
    it('should DELETE /auth/oauth/:provider/disconnect', async () => {
      mockDelete.mockResolvedValueOnce({ data: undefined });
      await oauthService.disconnect('google');
      expect(mockDelete).toHaveBeenCalledWith('/auth/oauth/google/disconnect');
    });
  });

  describe('linkProvider', () => {
    it('should redirect with link param', async () => {
      const data = { authorization_url: 'https://login.microsoftonline.com/auth?link=true', state: 'st' };
      mockGet.mockResolvedValueOnce({ data });

      const originalLocation = window.location;
      const mockLocation = { ...originalLocation, href: '' } as Location;
      Object.defineProperty(window, 'location', { value: mockLocation, writable: true });

      await oauthService.linkProvider('microsoft');

      expect(mockGet).toHaveBeenCalledWith('/auth/oauth/microsoft/authorize', { params: { link: true } });
      expect(mockLocation.href).toBe('https://login.microsoftonline.com/auth?link=true');
      Object.defineProperty(window, 'location', { value: originalLocation, writable: true });
    });
  });
});
