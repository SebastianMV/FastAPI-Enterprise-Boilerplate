import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MFASettingsPage from './MFASettingsPage';

const mockGetStatus = vi.fn();
const mockSetup = vi.fn();
const mockVerify = vi.fn();
const mockDisable = vi.fn();

vi.mock('@/services/api', () => ({
  mfaService: {
    getStatus: (...args: unknown[]) => mockGetStatus(...args),
    setup: (...args: unknown[]) => mockSetup(...args),
    verify: (...args: unknown[]) => mockVerify(...args),
    disable: (...args: unknown[]) => mockDisable(...args),
  },
}));

// Mock clipboard
Object.assign(navigator, {
  clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
});

function renderPage() {
  return render(
    <MemoryRouter>
      <MFASettingsPage />
    </MemoryRouter>,
  );
}

describe('MFASettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner initially', () => {
    mockGetStatus.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows disabled status when MFA is off', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.disabled')).toBeInTheDocument();
    });
    expect(screen.getByText('mfa.inactive')).toBeInTheDocument();
  });

  it('shows enabled status when MFA is on', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: true, method: 'totp' });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.enabled')).toBeInTheDocument();
    });
    expect(screen.getByText('mfa.active')).toBeInTheDocument();
  });

  it('shows setup button when MFA is disabled', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.beginSetup')).toBeInTheDocument();
    });
  });

  it('starts setup flow on button click', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    mockSetup.mockResolvedValue({
      secret: 'JBSWY3DPEHPK3PXP',
      qr_code: 'data:image/png;base64,fake',
      backup_codes: ['code1', 'code2', 'code3', 'code4'],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.beginSetup')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('mfa.beginSetup'));
    await waitFor(() => {
      expect(screen.getByText('mfa.step1Title')).toBeInTheDocument();
    });
    expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument();
    expect(screen.getByText('mfa.step2Title')).toBeInTheDocument();
    expect(screen.getByText('mfa.step3Title')).toBeInTheDocument();
  });

  it('shows backup codes on toggle', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    mockSetup.mockResolvedValue({
      secret: 'SECRET',
      qr_code: 'data:image/png;base64,fake',
      backup_codes: ['backup1', 'backup2'],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.beginSetup')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('mfa.beginSetup'));
    await waitFor(() => {
      expect(screen.getByText('mfa.showCodes')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('mfa.showCodes'));
    expect(screen.getByText('backup1')).toBeInTheDocument();
    expect(screen.getByText('backup2')).toBeInTheDocument();
  });

  it('shows disable button when MFA is enabled', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: true, method: 'totp' });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.disable2fa')).toBeInTheDocument();
    });
  });

  it('shows disable form on button click', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: true, method: 'totp' });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.disable2fa')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('mfa.disable2fa'));
    expect(screen.getByText('mfa.current2faCode')).toBeInTheDocument();
    expect(screen.getByText('mfa.password')).toBeInTheDocument();
  });

  it('shows error message on fetch failure', async () => {
    mockGetStatus.mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.fetchError')).toBeInTheDocument();
    });
  });

  it('shows help section', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.aboutTitle')).toBeInTheDocument();
    });
  });

  it('renders back link to profile', async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('mfa.title')).toBeInTheDocument();
    });
    const backLink = document.querySelector('a[href="/profile"]');
    expect(backLink).toBeInTheDocument();
  });
});
