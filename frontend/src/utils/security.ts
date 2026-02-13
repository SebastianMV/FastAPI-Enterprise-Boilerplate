/**
 * Security utilities for frontend input validation and sanitization.
 *
 * Provides defense-in-depth measures for file uploads, URL validation,
 * input sanitization, and other security-sensitive operations.
 */

// =============================================================================
// File Upload Validation
// =============================================================================

export interface FileValidationOptions {
  /** Allowed MIME types (e.g., ['image/jpeg', 'image/png']) */
  allowedTypes: string[];
  /** Maximum file size in bytes */
  maxSizeBytes: number;
  /** Allowed file extensions (e.g., ['.jpg', '.png']) */
  allowedExtensions: string[];
}

export interface FileValidationResult {
  valid: boolean;
  /** i18n error code — callers must translate via `t(error, errorParams)` */
  error?: string;
  /** Interpolation params for the i18n error code */
  errorParams?: Record<string, unknown>;
}

const AVATAR_OPTIONS: FileValidationOptions = {
  allowedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  maxSizeBytes: 5 * 1024 * 1024, // 5MB
  allowedExtensions: ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
};

const IMPORT_OPTIONS: FileValidationOptions = {
  allowedTypes: [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  ],
  maxSizeBytes: 50 * 1024 * 1024, // 50MB
  allowedExtensions: ['.csv', '.xls', '.xlsx'],
};

/**
 * File validation error codes — callers must translate via i18n `t()`.
 *
 * Codes:
 * - `file.tooLarge`       — interpolation: `{ maxMB: number }`
 * - `file.empty`
 * - `file.invalidExtension` — interpolation: `{ allowed: string }`
 * - `file.invalidMimeType`  — interpolation: `{ allowed: string }`
 */
export function validateFile(file: File, options: FileValidationOptions): FileValidationResult {
  // Check file size
  if (file.size > options.maxSizeBytes) {
    const maxMB = Math.round(options.maxSizeBytes / (1024 * 1024));
    return { valid: false, error: 'file.tooLarge', errorParams: { maxMB } };
  }

  if (file.size === 0) {
    return { valid: false, error: 'file.empty' };
  }

  // Check file extension
  const fileName = file.name.toLowerCase();
  const hasValidExtension = options.allowedExtensions.some(ext =>
    fileName.endsWith(ext)
  );
  if (!hasValidExtension) {
    return {
      valid: false,
      error: 'file.invalidExtension',
      errorParams: { allowed: options.allowedExtensions.join(', ') },
    };
  }

  // Check MIME type (note: browser-reported, can be spoofed, but still useful as defense-in-depth)
  if (file.type && !options.allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: 'file.invalidMimeType',
      errorParams: { allowed: options.allowedTypes.join(', ') },
    };
  }

  return { valid: true };
}

export function validateAvatarFile(file: File): FileValidationResult {
  return validateFile(file, AVATAR_OPTIONS);
}

export function validateImportFile(file: File): FileValidationResult {
  return validateFile(file, IMPORT_OPTIONS);
}

// =============================================================================
// URL Validation
// =============================================================================

/** Known-safe OAuth provider domains */
const TRUSTED_OAUTH_DOMAINS = [
  'accounts.google.com',
  'github.com',
  'login.microsoftonline.com',
  'login.live.com',
  'appleid.apple.com',
];

/**
 * Validates that a URL is safe for redirection.
 * Only allows relative URLs starting with '/' (same-origin) that don't escape.
 */
export function isSafeRedirectUrl(url: string): boolean {
  if (!url || typeof url !== 'string') return false;

  // Decode URL-encoded characters to catch encoded bypasses (%2f%2f → //)
  let decoded: string;
  try {
    decoded = decodeURIComponent(url);
  } catch {
    return false; // Malformed percent-encoding
  }

  // Block dangerous schemes (check both raw and decoded)
  const lower = decoded.toLowerCase().trim();
  if (
    // eslint-disable-next-line no-script-url -- security check for dangerous URL schemes
    lower.startsWith('javascript:') ||
    lower.startsWith('data:') ||
    lower.startsWith('vbscript:') ||
    lower.startsWith('blob:')
  ) {
    return false;
  }

  // Must start with a single forward slash (not //)
  if (!decoded.startsWith('/') || decoded.startsWith('//')) return false;

  // Block path traversal
  if (decoded.includes('..')) return false;

  // Block backslash tricks
  if (decoded.includes('\\')) return false;

  return true;
}

/**
 * Validates a URL is safe for use as an image source.
 * Allows relative paths and HTTPS URLs; blocks dangerous schemes.
 */
export function isSafeImageUrl(url: string): boolean {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();
  if (!trimmed) return false;

  // Allow relative URLs
  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) return true;

  // Allow HTTPS URLs
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Validates that an OAuth authorization URL points to a trusted provider domain.
 * Matches exact hostnames only — does not allow arbitrary subdomains.
 */
export function isValidOAuthUrl(url: string): boolean {
  if (!url || typeof url !== 'string') return false;
  if (!url.startsWith('https://')) return false;

  try {
    const parsed = new URL(url);
    return TRUSTED_OAUTH_DOMAINS.some(domain =>
      parsed.hostname === domain
    );
  } catch {
    return false;
  }
}

// =============================================================================
// Input Sanitization
// =============================================================================

/**
 * Sanitizes a string for safe rendering.
 * Uses DOMParser to strip all HTML tags reliably, including unclosed tags.
 */
export function sanitizeText(input: string): string {
  if (typeof input !== 'string') return '';
  // Use DOMParser for robust HTML stripping (handles unclosed tags, edge cases)
  try {
    const doc = new DOMParser().parseFromString(input, 'text/html');
    return (doc.body.textContent ?? '').trim();
  } catch {
    // Fallback: regex-based stripping
    return input.replace(/<[^>]*>?/g, '').trim();
  }
}

/**
 * Sanitizes a search query to prevent search-engine injection.
 * Removes special characters that could be interpreted as operators.
 */
export function sanitizeSearchQuery(query: string, maxLength = 500): string {
  if (typeof query !== 'string') return '';
  // Remove Elasticsearch/Lucene special chars: + - = && || > < ! ( ) { } [ ] ^ " ~ * ? : \ /
  return query
    .replace(/[+\-=&|><!()[\]{}^"~*?:\\/]/g, ' ')
    .replace(/\b(AND|OR|NOT|TO)\b/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxLength);
}

/**
 * Validates and sanitizes a CSS color value.
 * Only allows hex colors (#fff, #ffffff, #ffffffaa).
 */
export function sanitizeCssColor(color: string): string {
  if (typeof color !== 'string') return '#000000';
  const hex = color.trim();
  if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(hex)) {
    return hex;
  }
  return '#000000';
}

/**
 * Sanitizes a filename for safe use in downloads.
 * Removes path separators, special characters, and Windows reserved device names.
 */
export function sanitizeFilename(name: string): string {
  if (typeof name !== 'string') return 'download';
  const WINDOWS_RESERVED = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$/i;
  let safe = name
    .replace(/[/\\:*?"<>|]/g, '_')
    .replace(/\.\./g, '_')    // Strip control characters (U+0000–U+001F, U+007F–U+009F)
    // eslint-disable-next-line no-control-regex
    .replace(/[\x00-\x1f\x7f-\x9f]/g, '')    .slice(0, 255);
  if (WINDOWS_RESERVED.test(safe)) {
    safe = `_${safe}`;
  }
  return safe || 'download';
}

// =============================================================================
// Input Bounds
// =============================================================================

/**
 * Clamps pagination parameters to safe bounds.
 */
export function clampPaginationParams(params?: { skip?: number; limit?: number }): { skip: number; limit: number } {
  const skip = Math.max(0, Math.floor(Number(params?.skip) || 0));
  const limit = Math.min(100, Math.max(1, Math.floor(Number(params?.limit) || 20)));
  return { skip, limit };
}

/**
 * Validates a password meets minimum security requirements.
 * Returns i18n error codes — callers must translate via `t(error, errorParams)`.
 */
export function validatePasswordStrength(password: string): { valid: boolean; error?: string; errorParams?: Record<string, unknown> } {
  if (!password || typeof password !== 'string') {
    return { valid: false, error: 'validation.passwordRequired' };
  }
  if (password.length < 8) {
    return { valid: false, error: 'validation.passwordMin', errorParams: { min: 8 } };
  }
  if (password.length > 256) {
    return { valid: false, error: 'validation.passwordMax', errorParams: { max: 256 } };
  }
  if (!/[A-Z]/.test(password)) {
    return { valid: false, error: 'validation.passwordUppercase' };
  }
  if (!/[a-z]/.test(password)) {
    return { valid: false, error: 'validation.passwordLowercase' };
  }
  if (!/[0-9]/.test(password)) {
    return { valid: false, error: 'validation.passwordDigit' };
  }
  if (!/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) {
    return { valid: false, error: 'validation.passwordSpecial' };
  }
  return { valid: true };
}

/**
 * Masks an email address for display (e.g., j***@example.com).
 */
export function maskEmail(email: string): string {
  if (!email || typeof email !== 'string') return '***';
  const [local, domain] = email.split('@');
  if (!local || !domain) return '***';
  const visibleChars = Math.min(2, local.length);
  return `${local.slice(0, visibleChars)}***@${domain}`;
}

/**
 * Masks an IP address for display (e.g., 192.168.x.x).
 */
export function maskIpAddress(ip: string): string {
  if (!ip || typeof ip !== 'string') return '***';
  // IPv4
  const parts = ip.split('.');
  if (parts.length === 4) {
    return `${parts[0]}.${parts[1]}.x.x`;
  }
  // IPv6 - show first 2 segments
  const v6parts = ip.split(':');
  if (v6parts.length > 2) {
    return `${v6parts[0]}:${v6parts[1]}:****`;
  }
  return '***';
}

/**
 * Validates that a QR code data URI is a safe PNG base64 image.
 */
export function isValidQrCodeUri(uri: string): boolean {
  if (typeof uri !== 'string') return false;
  return /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(uri);
}

/**
 * Safely decode a JWT payload (handles base64url encoding).
 */
export function safeDecodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    // Reject tokens larger than 10KB to prevent abuse
    if (token.length > 10240) return null;
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    // Convert base64url to standard base64
    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    // Pad if necessary
    while (base64.length % 4 !== 0) {
      base64 += '=';
    }
    const payload = JSON.parse(atob(base64));
    if (typeof payload !== 'object' || payload === null) return null;
    return payload;
  } catch {
    return null;
  }
}

/**
 * Validates a theme value from localStorage.
 */
export function validateTheme(value: unknown): 'light' | 'dark' | 'system' {
  if (value === 'light' || value === 'dark' || value === 'system') {
    return value;
  }
  return 'system';
}

/**
 * Validates that an action URL is safe for navigation.
 * Allows only relative paths starting with '/' that don't traverse.
 */
export function validateActionUrl(url: unknown): string | undefined {
  if (typeof url !== 'string' || !url) return undefined;
  return isSafeRedirectUrl(url) ? url : undefined;
}
