import api from './api';

// Email Verification Types
export interface VerificationStatus {
  email: string;
  email_verified: boolean;
  verification_required: boolean;
}

export const emailVerificationService = {
  sendVerification: async (): Promise<{ message: string; success: boolean }> => {
    const response = await api.post<{ message: string; success: boolean }>('/auth/send-verification');
    return response.data;
  },

  verifyEmail: async (token: string): Promise<{ message: string; success: boolean }> => {
    const response = await api.post<{ message: string; success: boolean }>('/auth/verify-email', { token });
    return response.data;
  },

  getStatus: async (): Promise<VerificationStatus> => {
    const response = await api.get<VerificationStatus>('/auth/verification-status');
    return response.data;
  },
};
