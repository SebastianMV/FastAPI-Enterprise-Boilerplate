import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import i18next from 'eslint-plugin-i18next';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2024,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      'jsx-a11y': jsxA11y,
      'i18next': i18next,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],

      // =====================================================================
      // i18n — detect hardcoded strings in JSX (prevents i18n regression)
      // From Audit 24 retrospective: ~157 fixes were i18n retrofit.
      // This rule catches new hardcoded strings at lint time.
      // =====================================================================
      'i18next/no-literal-string': ['warn', {
        markupOnly: true,
        ignoreAttribute: [
          'data-testid', 'className', 'class', 'id', 'key', 'type',
          'name', 'htmlFor', 'to', 'href', 'target', 'rel', 'role',
          'aria-label', 'aria-labelledby', 'aria-describedby',
          'autoComplete', 'method', 'encType', 'accept', 'tabIndex',
          'viewBox', 'fill', 'stroke', 'strokeWidth', 'strokeLinecap',
          'strokeLinejoin', 'd', 'cx', 'cy', 'r', 'x1', 'y1', 'x2', 'y2',
        ],
      }],

      // =====================================================================
      // Security rules — codified from 13 security audits
      // =====================================================================

      // Prevent console.log/error leaking to production (Audit 11, #346-350)
      // console.warn is allowed for dev-facing deprecation notices
      'no-console': ['error', { allow: ['warn'] }],

      // Prevent eval() and similar (CWE-95)
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',

      // Prevent script injection via innerHTML (CWE-79)
      'no-script-url': 'error',

      // Prevent dangerouslySetInnerHTML usage (CWE-79)
      // Uses no-restricted-syntax since eslint-plugin-react is not installed
      'no-restricted-syntax': ['error', {
        selector: 'JSXAttribute[name.name="dangerouslySetInnerHTML"]',
        message: 'Do not use dangerouslySetInnerHTML. Use sanitizeText() from @/utils/security instead.',
      }],
    },
  },
  // =========================================================================
  // Test file overrides — relax security rules for tests
  // =========================================================================
  {
    files: ['**/*.test.{ts,tsx}', '**/*.spec.{ts,tsx}', '**/test/**/*.{ts,tsx}'],
    rules: {
      'no-console': 'off',
    },
  },
);
