import api from "./api";

/** Validates that a verification token has a plausible format (non-empty, bounded length) */
function validateTokenFormat(token: string): void {
  if (
    !token ||
    typeof token !== "string" ||
    token.length < 10 ||
    token.length > 512
  ) {
    throw new Error("auth.invalidTokenFormat");
  }
  // Only allow URL-safe characters (alphanumeric, hyphens, underscores, dots, tildes)
  if (!/^[A-Za-z0-9._~-]+$/.test(token)) {
    throw new Error("auth.invalidTokenFormat");
  }
}

// Email Verification Types
export interface VerificationStatus {
  email: string;
  email_verified: boolean;
  verification_required: boolean;
}

export const emailVerificationService = {
  sendVerification: async (): Promise<{
    message: string;
    success: boolean;
  }> => {
    const response = await api.post<{ message: string; success: boolean }>(
      "/auth/send-verification",
    );
    return response.data;
  },

  verifyEmail: async (
    token: string,
  ): Promise<{ message: string; success: boolean }> => {
    validateTokenFormat(token);
    const response = await api.post<{ message: string; success: boolean }>(
      "/auth/verify-email",
      { token },
    );
    return response.data;
  },

  getStatus: async (): Promise<VerificationStatus> => {
    const response = await api.get<VerificationStatus>(
      "/auth/verification-status",
    );
    return response.data;
  },
};
