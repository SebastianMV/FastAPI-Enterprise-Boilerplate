import api from "./api";

/** Validates that a code is a 6-digit numeric string */
function validateMfaCode(code: string): void {
  if (!/^\d{6}$/.test(code)) {
    throw new Error("mfa.invalidCode");
  }
}

// MFA Types
export interface MFAStatus {
  is_enabled: boolean;
  enabled_at: string | null;
  backup_codes_remaining: number;
  last_used_at: string | null;
  email_otp_enabled?: boolean;
}

export interface MFASetupResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

export interface EmailOTPResponse {
  message: string;
  expires_in: number;
  cooldown_remaining?: number;
}

export const mfaService = {
  getStatus: async (): Promise<MFAStatus> => {
    const response = await api.get<MFAStatus>("/mfa/status");
    return response.data;
  },

  setup: async (): Promise<MFASetupResponse> => {
    const response = await api.post<MFASetupResponse>("/mfa/setup");
    return response.data;
  },

  verify: async (code: string): Promise<{ message: string }> => {
    validateMfaCode(code);
    const response = await api.post<{ message: string }>("/mfa/verify", {
      code,
    });
    return response.data;
  },

  disable: async (
    code: string,
    password: string,
  ): Promise<{ message: string }> => {
    validateMfaCode(code);
    const response = await api.post<{ message: string }>("/mfa/disable", {
      code,
      password,
    });
    return response.data;
  },

  regenerateBackupCodes: async (
    code: string,
  ): Promise<{ backup_codes: string[] }> => {
    validateMfaCode(code);
    const response = await api.post<{ backup_codes: string[] }>(
      "/mfa/backup-codes/regenerate",
      { code },
    );
    return response.data;
  },

  requestEmailOTP: async (): Promise<EmailOTPResponse> => {
    const response = await api.post<EmailOTPResponse>("/mfa/email-otp/request");
    return response.data;
  },

  verifyEmailOTP: async (
    code: string,
  ): Promise<{ message: string; valid: boolean }> => {
    validateMfaCode(code);
    const response = await api.post<{ message: string; valid: boolean }>(
      "/mfa/email-otp/verify",
      { code },
    );
    return response.data;
  },
};
