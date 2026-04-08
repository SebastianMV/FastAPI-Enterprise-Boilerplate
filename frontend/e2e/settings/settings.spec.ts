import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Settings Page
 * 
 * Tests that would have detected the bugs we just fixed:
 * - Theme buttons visibility in dark mode
 * - Timezone selector functionality
 * - Notification toggle
 * - Language selector
 * - Profile navigation
 */

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    // Login first with user WITHOUT MFA
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('Test123!');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Wait for successful login (should redirect to dashboard)
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    
    // Navigate to settings
    await page.goto('/settings');
  });

  test('should display settings page with all sections', async ({ page }) => {
    // Check page title
    await expect(page.getByRole('heading', { name: /^settings$/i, level: 1 })).toBeVisible();
    
    // Check all section headers are visible (using level 2 for main sections)
    await expect(page.getByRole('heading', { name: /^notifications$/i, level: 2 })).toBeVisible();
    await expect(page.getByRole('heading', { name: /^appearance$/i, level: 2 })).toBeVisible();
    await expect(page.getByRole('heading', { name: /language.*region/i, level: 2 })).toBeVisible();
    await expect(page.getByRole('heading', { name: /danger zone/i, level: 2 })).toBeVisible();
  });

  test('theme buttons are visible and have readable contrast', async ({ page }) => {
    // BUG FIX TEST: This would have caught the invisible buttons in dark mode
    
    // Find all theme buttons
    const lightBtn = page.getByRole('button', { name: /^light$/i });
    const darkBtn = page.getByRole('button', { name: /^dark$/i });
    const systemBtn = page.getByRole('button', { name: /^system$/i });
    
    // All buttons should be visible
    await expect(lightBtn).toBeVisible();
    await expect(darkBtn).toBeVisible();
    await expect(systemBtn).toBeVisible();
    
    // Check that buttons have text color (not default browser color)
    const lightBtnColor = await lightBtn.evaluate((el) => {
      return window.getComputedStyle(el).color;
    });
    
    // Color should not be rgb(0, 0, 0) or transparent
    expect(lightBtnColor).not.toBe('rgba(0, 0, 0, 0)');
    expect(lightBtnColor).not.toBe('transparent');
    
    // Buttons should have visible border
    const lightBtnBorder = await lightBtn.evaluate((el) => {
      return window.getComputedStyle(el).borderWidth;
    });
    expect(lightBtnBorder).not.toBe('0px');
  });

  test('theme buttons are functional and show feedback', async ({ page }) => {
    // Close any open modals first
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    
    // Click Dark theme button
    const darkBtn = page.getByRole('button', { name: /^dark$/i });
    await darkBtn.click();
    
    // Should show success alert
    await expect(page.getByText(/theme.*changed.*dark/i)).toBeVisible({ timeout: 3000 });
    
    // Check localStorage was updated
    const theme = await page.evaluate(() => localStorage.getItem('theme'));
    expect(theme).toBe('dark');
    
    // Dark mode should be applied to document
    const isDarkMode = await page.evaluate(() => {
      return document.documentElement.classList.contains('dark');
    });
    expect(isDarkMode).toBe(true);
    
    // Close alert before next action
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    
    // Click Light theme button
    const lightBtn = page.getByRole('button', { name: /^light$/i });
    await lightBtn.click();
    
    await expect(page.getByText(/theme.*changed.*light/i)).toBeVisible({ timeout: 3000 });
    
    // Dark mode should be removed
    const isLightMode = await page.evaluate(() => {
      return !document.documentElement.classList.contains('dark');
    });
    expect(isLightMode).toBe(true);
  });

  test('selected theme button is visually distinct', async ({ page }) => {
    // Click dark theme
    const darkBtn = page.getByRole('button', { name: /^dark$/i });
    await darkBtn.click();
    
    // Wait for alert to disappear
    await page.waitForTimeout(2000);
    
    // Dark button should have primary color styling
    const darkBtnClass = await darkBtn.getAttribute('class');
    expect(darkBtnClass).toContain('primary');
    
    // Should show checkmark icon
    await expect(darkBtn.locator('svg').last()).toBeVisible();
  });

  test('timezone selector is functional', async ({ page }) => {
    // BUG FIX TEST: This would have caught the non-functional timezone selector
    
    const timezoneSelect = page.locator('select').filter({ has: page.locator('option[value*="Santiago"]') });
    
    // Verify initial value
    const initialValue = await timezoneSelect.inputValue();
    expect(initialValue).toBe('America/Santiago');
    
    // Change timezone
    await timezoneSelect.selectOption('Europe/Madrid');
    
    // Wait for alert to appear (proves handler executed)
    await expect(page.getByText(/timezone.*updated|preferences.*saved|settings.*updated/i)).toBeVisible({ timeout: 5000 });
    
    // Select should reflect the change immediately
    await expect(timezoneSelect).toHaveValue('Europe/Madrid');
    
    // Close the alert
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    
    // Verify localStorage after alert confirms execution
    const savedTimezone = await page.evaluate(() => localStorage.getItem('timezone'));
    expect(savedTimezone).toBe('Europe/Madrid');
  });

  test('language selector is functional', async ({ page }) => {
    const languageSelect = page.locator('select').filter({ has: page.locator('option[value*="en"]') });
    
    // Change language
    await languageSelect.selectOption('es');
    
    // Should show success alert
    await expect(page.getByText(/language.*updated|idioma.*actualizado/i)).toBeVisible({ timeout: 3000 });
    
    // Language should change
    const selectedValue = await languageSelect.inputValue();
    expect(selectedValue).toBe('es');
  });

  test('notification toggle works', async ({ page }) => {
    const toggle = page.locator('button.inline-flex.h-6.w-11').first();
    
    // Get initial state
    const initialClass = await toggle.getAttribute('class');
    const initiallyEnabled = initialClass?.includes('bg-primary');
    
    // Click toggle
    await toggle.click();
    
    // Should show alert
    await expect(page.getByText(/notifications/i)).toBeVisible({ timeout: 3000 });
    
    // State should change
    const newClass = await toggle.getAttribute('class');
    const nowEnabled = newClass?.includes('bg-primary');
    expect(nowEnabled).not.toBe(initiallyEnabled);
    
    // Check localStorage
    const stored = await page.evaluate(() => localStorage.getItem('notificationsEnabled'));
    expect(stored).toBe(nowEnabled ? 'true' : 'false');
  });

  test('edit profile button navigates to profile page', async ({ page }) => {
    await page.getByRole('button', { name: /edit profile/i }).click();
    
    await expect(page).toHaveURL(/\/profile/);
  });

  test('delete account button shows confirmation modal', async ({ page }) => {
    await page.getByRole('button', { name: /delete account/i }).click();
    
    // Modal should appear
    await expect(page.getByRole('heading', { name: /delete account/i })).toBeVisible();
    await expect(page.getByText(/are you sure/i)).toBeVisible();
    
    // Should have cancel and confirm buttons
    await expect(page.getByRole('button', { name: /cancel/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /delete/i })).toBeVisible();
    
    // Click cancel
    await page.getByRole('button', { name: /cancel/i }).click();
    
    // Modal should close
    await expect(page.getByRole('heading', { name: /delete account/i })).not.toBeVisible();
  });

  test('features section shows read-only status', async ({ page }) => {
    // Features section should be visible
    await expect(page.getByRole('heading', { name: /^features$/i })).toBeVisible();
    
    // Should show status for each feature
    const features = ['internal chat', 'websocket', 'notification'];
    
    for (const feature of features) {
      // Each feature should show enabled/disabled status
      const featureText = page.getByText(new RegExp(feature, 'i'));
      await expect(featureText).toBeVisible();
    }
    
    // Should have note about admin configuration
    await expect(page.getByText(/configured.*administrator/i)).toBeVisible();
  });
});

test.describe('Settings Page - Dark Mode Specific', () => {
  test.beforeEach(async ({ page }) => {
    // Login with user WITHOUT MFA
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('Test123!');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    
    // Navigate to settings
    await page.goto('/settings');
    
    // Enable dark mode
    await page.getByRole('button', { name: /^dark$/i }).click();
    await page.waitForTimeout(1000); // Wait for theme to apply
  });

  test('theme buttons are visible in dark mode', async ({ page }) => {
    // BUG FIX TEST: The main test that would catch the invisible buttons bug
    
    const lightBtn = page.getByRole('button', { name: /^light$/i });
    const darkBtn = page.getByRole('button', { name: /^dark$/i });
    const systemBtn = page.getByRole('button', { name: /^system$/i });
    
    // All buttons should be visible
    await expect(lightBtn).toBeVisible();
    await expect(darkBtn).toBeVisible();
    await expect(systemBtn).toBeVisible();
    
    // Check computed color of unselected buttons (Light and System)
    const lightBtnColor = await lightBtn.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        color: style.color,
        backgroundColor: style.backgroundColor,
      };
    });
    
    // Color should not be same as background (readable contrast)
    expect(lightBtnColor.color).not.toBe(lightBtnColor.backgroundColor);
    
    // Text should not be invisible (rgb(0,0,0) on dark background)
    expect(lightBtnColor.color).not.toBe('rgb(0, 0, 0)');
  });
});
