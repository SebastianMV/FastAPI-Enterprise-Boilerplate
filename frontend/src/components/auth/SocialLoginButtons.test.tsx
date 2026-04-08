/**
 * Unit tests for SocialLoginButtons component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SocialLoginButtons from './SocialLoginButtons';

const mockRedirectToProvider = vi.fn();
const mockLinkProvider = vi.fn();

vi.mock('@/services/api', () => ({
  oauthService: {
    redirectToProvider: (...args: unknown[]) => mockRedirectToProvider(...args),
    linkProvider: (...args: unknown[]) => mockLinkProvider(...args),
  },
  OAUTH_PROVIDERS: [
    { id: 'google', name: 'Google', icon: 'google', color: '#4285F4' },
    { id: 'github', name: 'GitHub', icon: 'github', color: '#333333' },
    { id: 'microsoft', name: 'Microsoft', icon: 'microsoft', color: '#00A4EF' },
  ],
}));

describe('SocialLoginButtons', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should render buttons for all providers', () => {
    render(<SocialLoginButtons />);
    expect(screen.getByText(/Google/)).toBeInTheDocument();
    expect(screen.getByText(/GitHub/)).toBeInTheDocument();
    expect(screen.getByText(/Microsoft/)).toBeInTheDocument();
  });

  it('should show "Continue with" in login mode', () => {
    render(<SocialLoginButtons mode="login" />);
    expect(screen.getByText('oauth.continueWith Google')).toBeInTheDocument();
  });

  it('should show "Sign up with" in register mode', () => {
    render(<SocialLoginButtons mode="register" />);
    expect(screen.getByText('oauth.signUpWith Google')).toBeInTheDocument();
  });

  it('should show "Connect" in link mode', () => {
    render(<SocialLoginButtons mode="link" />);
    expect(screen.getByText('oauth.connect Google')).toBeInTheDocument();
  });

  it('should call redirectToProvider on click in login mode', async () => {
    mockRedirectToProvider.mockResolvedValueOnce(undefined);
    render(<SocialLoginButtons />);
    fireEvent.click(screen.getByText('oauth.continueWith GitHub'));
    await waitFor(() => {
      expect(mockRedirectToProvider).toHaveBeenCalledWith('github');
    });
  });

  it('should call linkProvider on click in link mode', async () => {
    mockLinkProvider.mockResolvedValueOnce(undefined);
    render(<SocialLoginButtons mode="link" />);
    fireEvent.click(screen.getByText('oauth.connect Google'));
    await waitFor(() => {
      expect(mockLinkProvider).toHaveBeenCalledWith('google');
    });
  });

  it('should call onError when redirect fails', async () => {
    const onError = vi.fn();
    mockRedirectToProvider.mockRejectedValueOnce(new Error('OAuth unavailable'));
    render(<SocialLoginButtons onError={onError} />);
    fireEvent.click(screen.getByText('oauth.continueWith Google'));
    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('oauth.connectionFailed');
    });
  });

  it('should disable all buttons while loading', async () => {
    // Never resolves to keep loading state
    mockRedirectToProvider.mockReturnValueOnce(new Promise(() => {}));
    render(<SocialLoginButtons />);
    fireEvent.click(screen.getByText('oauth.continueWith Google'));
    await waitFor(() => {
      const buttons = screen.getAllByRole('button');
      buttons.forEach(btn => expect(btn).toBeDisabled());
    });
  });
});
