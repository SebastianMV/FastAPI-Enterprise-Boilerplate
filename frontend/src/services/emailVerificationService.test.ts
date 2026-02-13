/**
 * Unit tests for emailVerificationService and configService.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('./api', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

import { emailVerificationService } from './emailVerificationService';
import { configService } from './configService';

describe('emailVerificationService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should send verification', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'Sent', success: true } });
    const result = await emailVerificationService.sendVerification();
    expect(mockPost).toHaveBeenCalledWith('/auth/send-verification');
    expect(result.success).toBe(true);
  });

  it('should verify email with token', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'Verified', success: true } });
    const result = await emailVerificationService.verifyEmail('abcdefghij-verification-token');
    expect(mockPost).toHaveBeenCalledWith('/auth/verify-email', { token: 'abcdefghij-verification-token' });
    expect(result.success).toBe(true);
  });

  it('should get verification status', async () => {
    const status = { email: 'a@b.com', email_verified: false, verification_required: true };
    mockGet.mockResolvedValueOnce({ data: status });
    const result = await emailVerificationService.getStatus();
    expect(mockGet).toHaveBeenCalledWith('/auth/verification-status');
    expect(result.verification_required).toBe(true);
  });
});

describe('configService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should get features', async () => {
    const features = { websocket_enabled: true, websocket_notifications: false };
    mockGet.mockResolvedValueOnce({ data: features });
    const result = await configService.getFeatures();
    expect(mockGet).toHaveBeenCalledWith('/config/features');
    expect(result.websocket_enabled).toBe(true);
  });
});
