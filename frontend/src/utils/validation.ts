/**
 * Shared form validation patterns.
 *
 * Centralizes regex patterns so every form (Login, Register, Users,
 * Profile, ForgotPassword) uses the same rules.
 */

/** RFC-5322-ish email validation (same pattern used throughout the app). */
export const EMAIL_PATTERN = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i;

/**
 * Password complexity — requires at least one lowercase, one uppercase,
 * one digit, and one special character.
 */
export const PASSWORD_PATTERN =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>])/;

/** Minimum password length enforced on the client side. */
export const PASSWORD_MIN_LENGTH = 8;

/** Maximum password length (defense against long-input DoS). */
export const PASSWORD_MAX_LENGTH = 128;
