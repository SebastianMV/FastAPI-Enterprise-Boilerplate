/**
 * Unit tests for ConnectedAccounts component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ConnectedAccounts from './ConnectedAccounts';

const mockGetConnections = vi.fn();
const mockDisconnect = vi.fn();
const mockLinkProvider = vi.fn();

vi.mock('@/services/api', () => ({
  oauthService: {
    getConnections: () => mockGetConnections(),
    disconnect: (...a: unknown[]) => mockDisconnect(...a),
    linkProvider: (...a: unknown[]) => mockLinkProvider(...a),
  },
}));

describe('ConnectedAccounts', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should show loading state initially', () => {
    mockGetConnections.mockReturnValue(new Promise(() => {}));
    render(<ConnectedAccounts />);
    // Loader2 renders as svg with animate-spin class
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('should render provider list after loading', async () => {
    mockGetConnections.mockResolvedValueOnce([]);
    render(<ConnectedAccounts />);
    await waitFor(() => {
      expect(screen.getByText('profile.connectedAccounts')).toBeInTheDocument();
      expect(screen.getByText('Google')).toBeInTheDocument();
      expect(screen.getByText('GitHub')).toBeInTheDocument();
      expect(screen.getByText('Microsoft')).toBeInTheDocument();
    });
  });

  it('should show "Not connected" for unlinked providers', async () => {
    mockGetConnections.mockResolvedValueOnce([]);
    render(<ConnectedAccounts />);
    await waitFor(() => {
      const notConnected = screen.getAllByText('profile.notConnected');
      expect(notConnected).toHaveLength(3);
    });
  });

  it('should show "Connect" buttons for unlinked providers', async () => {
    mockGetConnections.mockResolvedValueOnce([]);
    render(<ConnectedAccounts />);
    await waitFor(() => {
      const connectBtns = screen.getAllByText('profile.connect');
      expect(connectBtns).toHaveLength(3);
    });
  });

  it('should show "Disconnect" for linked provider', async () => {
    mockGetConnections.mockResolvedValueOnce([
      { id: 'c1', provider: 'google', provider_email: 'me@gmail.com' },
    ]);
    render(<ConnectedAccounts />);
    await waitFor(() => {
      expect(screen.getByText('profile.disconnect')).toBeInTheDocument();
      expect(screen.getByText('profile.connectedAs')).toBeInTheDocument();
    });
  });

  it('should disconnect a provider', async () => {
    mockGetConnections.mockResolvedValueOnce([
      { id: 'c1', provider: 'google', provider_email: 'me@gmail.com' },
    ]);
    mockDisconnect.mockResolvedValueOnce(undefined);
    render(<ConnectedAccounts />);
    await waitFor(() => screen.getByText('profile.disconnect'));
    fireEvent.click(screen.getByText('profile.disconnect'));
    await waitFor(() => {
      expect(mockDisconnect).toHaveBeenCalledWith('google');
    });
  });

  it('should handle getConnections error gracefully', async () => {
    mockGetConnections.mockRejectedValueOnce(new Error('Network error'));
    render(<ConnectedAccounts />);
    await waitFor(() => {
      // Should render with empty connections
      expect(screen.getByText('profile.connectedAccounts')).toBeInTheDocument();
    });
  });

  it('should render info box', async () => {
    mockGetConnections.mockResolvedValueOnce([]);
    render(<ConnectedAccounts />);
    await waitFor(() => {
      expect(screen.getByText('profile.whyConnect')).toBeInTheDocument();
    });
  });
});
