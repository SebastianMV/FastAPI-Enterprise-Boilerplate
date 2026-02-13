/**
 * Unit tests for ConnectedAccounts component.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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

vi.mock('@/components/common/Modal', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  ConfirmModal: ({ isOpen, onConfirm, title }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        <h2>{title}</h2>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
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
    // Confirm in the modal
    await waitFor(() => {
      expect(screen.getByTestId('confirm-modal')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Confirm'));
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
