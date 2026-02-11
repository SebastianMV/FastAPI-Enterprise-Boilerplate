import api from './api';

// OAuth Types
export interface OAuthProvider {
  id: string;
  name: string;
  icon: string;
  color: string;
}

export interface OAuthAuthorizeResponse {
  authorization_url: string;
  state: string;
}

export interface OAuthConnection {
  id: string;
  provider: string;
  provider_email: string | null;
  provider_username: string | null;
  provider_display_name: string | null;
  provider_avatar_url: string | null;
  is_primary: boolean;
  last_used_at: string | null;
  created_at: string | null;
}

export const OAUTH_PROVIDERS: OAuthProvider[] = [
  { id: 'google', name: 'Google', icon: 'google', color: '#4285F4' },
  { id: 'github', name: 'GitHub', icon: 'github', color: '#333333' },
  { id: 'microsoft', name: 'Microsoft', icon: 'microsoft', color: '#00A4EF' },
];

export const oauthService = {
  getAuthorizationUrl: async (provider: string): Promise<OAuthAuthorizeResponse> => {
    const response = await api.get<OAuthAuthorizeResponse>(
      `/auth/oauth/${encodeURIComponent(provider)}/authorize`
    );
    return response.data;
  },

  redirectToProvider: async (provider: string): Promise<void> => {
    const { authorization_url } = await oauthService.getAuthorizationUrl(provider);
    // Validate URL is HTTPS to prevent open redirect attacks
    if (!authorization_url || !authorization_url.startsWith('https://')) {
      throw new Error('Invalid authorization URL');
    }
    window.location.href = authorization_url;
  },

  getConnections: async (): Promise<OAuthConnection[]> => {
    const response = await api.get<OAuthConnection[]>('/auth/oauth/connections');
    return response.data;
  },

  disconnect: async (provider: string): Promise<void> => {
    await api.delete(`/auth/oauth/${encodeURIComponent(provider)}/disconnect`);
  },

  linkProvider: async (provider: string): Promise<void> => {
    const response = await api.get<OAuthAuthorizeResponse>(
      `/auth/oauth/${encodeURIComponent(provider)}/authorize`,
      { params: { link: true } }
    );
    const { authorization_url } = response.data;
    // Validate URL is HTTPS to prevent open redirect attacks
    if (!authorization_url || !authorization_url.startsWith('https://')) {
      throw new Error('Invalid authorization URL');
    }
    window.location.href = authorization_url;
  },
};
