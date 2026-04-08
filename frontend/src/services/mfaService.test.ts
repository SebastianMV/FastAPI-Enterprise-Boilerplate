/**
 * Unit tests for mfaService.
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

import { mfaService } from './mfaService';

describe('mfaService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should get MFA status', async () => {
    const status = { is_enabled: false, backup_codes_remaining: 0 };
    mockGet.mockResolvedValueOnce({ data: status });
    const result = await mfaService.getStatus();
    expect(mockGet).toHaveBeenCalledWith('/mfa/status');
    expect(result.is_enabled).toBe(false);
  });

  it('should setup MFA', async () => {
    const setup = { secret: 'ABCD', qr_code: 'data:image/png;base64,...', backup_codes: ['a', 'b'] };
    mockPost.mockResolvedValueOnce({ data: setup });
    const result = await mfaService.setup();
    expect(mockPost).toHaveBeenCalledWith('/mfa/setup');
    expect(result.secret).toBe('ABCD');
    expect(result.backup_codes).toHaveLength(2);
  });

  it('should verify MFA code', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'MFA enabled' } });
    const result = await mfaService.verify('123456');
    expect(mockPost).toHaveBeenCalledWith('/mfa/verify', { code: '123456' });
    expect(result.message).toBe('MFA enabled');
  });

  it('should disable MFA', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'MFA disabled' } });
    const result = await mfaService.disable('123456', 'mypassword');
    expect(mockPost).toHaveBeenCalledWith('/mfa/disable', { code: '123456', password: 'mypassword' });
    expect(result.message).toBe('MFA disabled');
  });

  it('should regenerate backup codes', async () => {
    mockPost.mockResolvedValueOnce({ data: { backup_codes: ['x', 'y', 'z'] } });
    const result = await mfaService.regenerateBackupCodes('123456');
    expect(mockPost).toHaveBeenCalledWith('/mfa/backup-codes/regenerate', { code: '123456' });
    expect(result.backup_codes).toHaveLength(3);
  });

  it('should request email OTP', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'OTP sent', expires_in: 300 } });
    const result = await mfaService.requestEmailOTP();
    expect(mockPost).toHaveBeenCalledWith('/mfa/email-otp/request');
    expect(result.expires_in).toBe(300);
  });

  it('should verify email OTP', async () => {
    mockPost.mockResolvedValueOnce({ data: { message: 'Valid', valid: true } });
    const result = await mfaService.verifyEmailOTP('654321');
    expect(mockPost).toHaveBeenCalledWith('/mfa/email-otp/verify', { code: '654321' });
    expect(result.valid).toBe(true);
  });
});
