import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import HttpBackend from 'i18next-http-backend';

// Supported languages
export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pt', name: 'Português', flag: '🇧🇷' },
] as const;

export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]['code'];

/**
 * i18n Configuration
 * 
 * Features:
 * - Lazy loading: Translations loaded on-demand via HTTP Backend
 * - Language detection: Auto-detect from browser/localStorage
 * - Code splitting: Only loads needed translations
 * - Production optimized: Reduces initial bundle size
 * 
 * For development with static imports, see: docs/I18N.md
 */
i18n
  // Load translations on-demand (lazy loading)
  .use(HttpBackend)
  // Detect user language from browser
  .use(LanguageDetector)
  // Pass i18n instance to react-i18next
  .use(initReactI18next)
  // Initialize
  .init({
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_LANGUAGES.map((l) => l.code),

    // Backend options for lazy loading
    backend: {
      loadPath: '/locales/{{lng}}.json',
      // Preload critical languages on app start (EN, ES, PT)
      preload: ['en', 'es', 'pt'],
    },

    // Detection options
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },

    interpolation: {
      escapeValue: false, // React already handles XSS
    },

    // React specific options
    react: {
      useSuspense: true,
    },

    // Performance optimizations
    load: 'currentOnly', // Only load current language (not all fallbacks)
    ns: 'translation', // Single namespace for simplicity
    defaultNS: 'translation',

    // Development helpers
    debug: import.meta.env.DEV && false, // Enable for debugging (set to true)
  });

export default i18n;
