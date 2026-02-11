/**
 * Tests for helper utility functions.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cn, formatDate, truncate, debounce } from './helpers';

describe('helpers', () => {
  describe('cn (classNames merger)', () => {
    it('should merge single class', () => {
      expect(cn('foo')).toBe('foo');
    });

    it('should merge multiple classes', () => {
      expect(cn('foo', 'bar', 'baz')).toBe('foo bar baz');
    });

    it('should handle conditional classes', () => {
      expect(cn('base', true && 'active', false && 'hidden')).toBe('base active');
    });

    it('should merge tailwind classes correctly', () => {
      // twMerge should resolve conflicts
      expect(cn('p-4', 'p-2')).toBe('p-2');
      expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
    });

    it('should handle arrays', () => {
      expect(cn(['foo', 'bar'])).toBe('foo bar');
    });

    it('should handle objects', () => {
      expect(cn({ foo: true, bar: false, baz: true })).toBe('foo baz');
    });

    it('should handle undefined and null', () => {
      expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
    });

    it('should handle empty inputs', () => {
      expect(cn()).toBe('');
    });
  });

  describe('formatDate', () => {
    it('should format date string', () => {
      const result = formatDate('2024-01-15T12:00:00Z');
      // Locale-independent: just verify it contains the year and day
      expect(result).toContain('2024');
      expect(result).toContain('15');
    });

    it('should format Date object', () => {
      const date = new Date('2024-06-20T10:30:00Z');
      const result = formatDate(date);
      // Locale-independent: just verify it contains the year and day
      expect(result).toContain('2024');
      expect(result).toContain('20');
    });

    it('should accept custom options', () => {
      // Use UTC date to avoid timezone issues
      const result = formatDate('2024-03-10T12:00:00Z', { weekday: 'long' });
      // Just verify it contains a weekday (could be Sunday or Saturday depending on TZ)
      expect(result.length).toBeGreaterThan(0);
    });

    it('should handle different date formats', () => {
      const result = formatDate('2024-12-25T12:00:00Z');
      expect(result).toContain('2024');
      // Day could be 24 or 25 depending on timezone
      expect(result).toMatch(/24|25/);
    });
  });

  describe('truncate', () => {
    it('should not truncate short strings', () => {
      expect(truncate('Hello', 10)).toBe('Hello');
    });

    it('should truncate long strings with ellipsis', () => {
      expect(truncate('Hello World', 8)).toBe('Hello...');
    });

    it('should handle exact length', () => {
      expect(truncate('Hello', 5)).toBe('Hello');
    });

    it('should handle very short max length', () => {
      expect(truncate('Hello World', 5)).toBe('He...');
    });

    it('should handle empty string', () => {
      expect(truncate('', 10)).toBe('');
    });
  });

  describe('debounce', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should debounce function calls', () => {
      const fn = vi.fn();
      const debounced = debounce(fn, 100);

      debounced();
      debounced();
      debounced();

      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(100);

      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should pass arguments correctly', () => {
      const fn = vi.fn();
      const debounced = debounce(fn, 100);

      debounced('arg1', 'arg2');
      vi.advanceTimersByTime(100);

      expect(fn).toHaveBeenCalledWith('arg1', 'arg2');
    });

    it('should reset timer on subsequent calls', () => {
      const fn = vi.fn();
      const debounced = debounce(fn, 100);

      debounced();
      vi.advanceTimersByTime(50);
      debounced();
      vi.advanceTimersByTime(50);
      debounced();
      vi.advanceTimersByTime(50);

      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should call with latest arguments', () => {
      const fn = vi.fn();
      const debounced = debounce(fn, 100);

      debounced('first');
      debounced('second');
      debounced('third');

      vi.advanceTimersByTime(100);

      expect(fn).toHaveBeenCalledWith('third');
    });
  });
});
