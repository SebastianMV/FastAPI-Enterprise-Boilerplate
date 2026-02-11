/**
 * Unit tests for LanguageSelector component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LanguageSelector } from './LanguageSelector';

// Mock react-i18next
const mockChangeLanguage = vi.fn().mockResolvedValue(undefined);
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: 'en',
      changeLanguage: mockChangeLanguage,
    },
  }),
}));

// Mock i18n config
vi.mock('../../i18n', () => ({
  SUPPORTED_LANGUAGES: [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'pt', name: 'Português', flag: '🇧🇷' },
  ],
}));

describe('LanguageSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe('Dropdown variant (default)', () => {
    it('should render dropdown button', () => {
      render(<LanguageSelector />);
      
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should show current language flag by default', () => {
      render(<LanguageSelector />);
      
      // Flag should be visible in the button (dropdown is closed)
      const flags = screen.getAllByText('🇺🇸');
      expect(flags.length).toBeGreaterThanOrEqual(1);
    });

    it('should show current language name when showLabel is true', () => {
      render(<LanguageSelector showLabel={true} />);
      
      // Name shown in button (dropdown is closed)
      const englishTexts = screen.getAllByText('English');
      expect(englishTexts.length).toBeGreaterThanOrEqual(1);
    });

    it('should hide flag when showFlags is false', async () => {
      const user = userEvent.setup();
      render(<LanguageSelector showFlags={false} />);
      
      // Even after opening, no flags should appear
      await user.click(screen.getByRole('button'));
      expect(screen.queryByText('🇺🇸')).not.toBeInTheDocument();
    });

    it('should render dropdown menu with all languages', async () => {
      const user = userEvent.setup();
      render(<LanguageSelector />);
      
      // Click button to open dropdown
      await user.click(screen.getByRole('button'));
      
      // Check dropdown contains all languages
      expect(screen.getByRole('listbox')).toBeInTheDocument();
      // Main button has role 'button', options have role 'option'
      expect(screen.getAllByRole('option')).toHaveLength(3); // 3 language options
    });

    it('should apply custom className', () => {
      render(<LanguageSelector className="custom-class" />);
      
      const container = screen.getByRole('button').parentElement?.parentElement;
      expect(container).toHaveClass('custom-class');
    });
  });

  describe('Inline variant', () => {
    it('should render inline buttons for each language', () => {
      render(<LanguageSelector variant="inline" />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(3); // 3 language buttons
    });

    it('should show language codes', () => {
      render(<LanguageSelector variant="inline" />);
      
      expect(screen.getByText('EN')).toBeInTheDocument();
      expect(screen.getByText('ES')).toBeInTheDocument();
      expect(screen.getByText('PT')).toBeInTheDocument();
    });

    it('should show flags when showFlags is true', () => {
      render(<LanguageSelector variant="inline" showFlags={true} />);
      
      expect(screen.getByText('🇺🇸')).toBeInTheDocument();
      expect(screen.getByText('🇪🇸')).toBeInTheDocument();
    });

    it('should call changeLanguage when a language button is clicked', async () => {
      const user = userEvent.setup();
      render(<LanguageSelector variant="inline" />);
      
      await user.click(screen.getByText('ES'));
      
      expect(mockChangeLanguage).toHaveBeenCalledWith('es');
    });

    it('should update document lang attribute', async () => {
      const user = userEvent.setup();
      render(<LanguageSelector variant="inline" />);
      
      await user.click(screen.getByText('PT'));
      
      expect(document.documentElement.lang).toBe('pt');
    });
  });

  describe('Accessibility', () => {
    it('should have proper aria-label for inline buttons', () => {
      render(<LanguageSelector variant="inline" />);
      
      const buttons = screen.getAllByRole('button', { name: /settings.switchToLanguage/i });
      expect(buttons.length).toBeGreaterThanOrEqual(2);
    });

    it('should have aria-pressed for current language in inline mode', () => {
      render(<LanguageSelector variant="inline" />);
      
      const buttons = screen.getAllByRole('button', { name: /settings.switchToLanguage/i });
      // First button (EN) should be pressed since default language is English
      expect(buttons[0]).toHaveAttribute('aria-pressed', 'true');
      // Second button (ES) should not be pressed
      expect(buttons[1]).toHaveAttribute('aria-pressed', 'false');
    });

    it('should have aria-haspopup for dropdown variant', () => {
      render(<LanguageSelector variant="dropdown" />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-haspopup', 'listbox');
    });

    it('should have listbox role for dropdown menu', async () => {
      const user = userEvent.setup();
      render(<LanguageSelector />);
      
      // Click button to open dropdown
      await user.click(screen.getByRole('button'));
      
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });
  });
});
