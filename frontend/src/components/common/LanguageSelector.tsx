import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from '../../i18n';

interface LanguageSelectorProps {
  variant?: 'dropdown' | 'inline';
  showFlags?: boolean;
  showLabel?: boolean;
  className?: string;
}

/**
 * Language selector component for switching application locale.
 *
 * @example
 * // Dropdown variant (default)
 * <LanguageSelector />
 *
 * // Inline buttons
 * <LanguageSelector variant="inline" showFlags />
 */
export function LanguageSelector({
  variant = 'dropdown',
  showFlags = true,
  showLabel = true,
  className = '',
}: LanguageSelectorProps) {
  const { i18n, t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && e.target instanceof Node && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const currentLanguage = SUPPORTED_LANGUAGES.find(
    (lang) => lang.code === i18n.language
  );

  const handleLanguageChange = (langCode: SupportedLanguage) => {
    i18n.changeLanguage(langCode);
    // Also update document lang attribute for accessibility
    document.documentElement.lang = langCode;
  };

  if (variant === 'inline') {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        {SUPPORTED_LANGUAGES.map((lang) => (
          <button
            key={lang.code}
            onClick={() => handleLanguageChange(lang.code)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors
              ${
                i18n.language === lang.code
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
              }`}
            aria-label={t('settings.switchToLanguage', { language: lang.name })}
            aria-pressed={i18n.language === lang.code}
          >
            {showFlags && <span className="mr-1">{lang.flag}</span>}
            {lang.code.toUpperCase()}
          </button>
        ))}
      </div>
    );
  }

  // Dropdown variant
  return (
    <div className={`relative inline-block ${className}`} ref={dropdownRef}>
      <div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 
                     bg-white border border-gray-300 rounded-md shadow-sm 
                     hover:bg-gray-50 focus:outline-none focus:ring-2 
                     focus:ring-primary-500 focus:border-primary-500
                     dark:bg-gray-800 dark:border-gray-600 dark:text-gray-300 
                     dark:hover:bg-gray-700"
          aria-haspopup="listbox"
          aria-expanded={isOpen}
        >
          <Globe className="w-4 h-4" />
          {showFlags && currentLanguage && (
            <span>{currentLanguage.flag}</span>
          )}
          {showLabel && currentLanguage && (
            <span>{currentLanguage.name}</span>
          )}
        </button>

        {/* Dropdown menu */}
        {isOpen && (
        <div
          className="absolute right-0 z-50 mt-2 w-48 origin-top-right rounded-md 
                     bg-white shadow-lg ring-1 ring-black ring-opacity-5 
                     dark:bg-gray-800 dark:ring-gray-700"
          role="listbox"
          aria-label={t('settings.language')}
        >
          <div className="py-1">
            {SUPPORTED_LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => {
                  handleLanguageChange(lang.code);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-2 text-sm
                  ${
                    i18n.language === lang.code
                      ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                  }`}
                role="option"
                aria-selected={i18n.language === lang.code}
              >
                {showFlags && <span className="text-lg">{lang.flag}</span>}
                <span>{lang.name}</span>
                {i18n.language === lang.code && (
                  <span className="ml-auto text-primary-600 dark:text-primary-400">
                    ✓
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
        )}
      </div>
    </div>
  );
}

export default LanguageSelector;
