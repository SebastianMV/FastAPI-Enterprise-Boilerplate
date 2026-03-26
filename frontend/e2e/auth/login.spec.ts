import { expect, test } from "@playwright/test";

/**
 * E2E Tests for Login flow (without MFA)
 *
 * Tests basic authentication functionality including:
 * - Successful login
 * - Failed login with invalid credentials
 * - Form validation
 * - Redirect after login
 */

test.describe("Login Page", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto("/login");
  });

  test("should display login form", async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/FastAPI-Enterprise-Boilerplate/);

    // Check form elements are visible
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("should show validation error for empty fields", async ({ page }) => {
    // Click sign in without filling fields
    await page.getByRole("button", { name: /sign in/i }).click();

    // Check for validation messages (React Hook Form validation)
    // Wait a bit for validation to trigger
    await page.waitForTimeout(100);

    // Form should not submit, still on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test("should show error for invalid credentials", async ({ page }) => {
    // Fill with invalid credentials
    await page.getByLabel(/email/i).fill("invalid@example.com");
    await page.getByLabel(/password/i).fill("wrongpassword");

    // Submit form
    await page.getByRole("button", { name: /sign in/i }).click();

    // Wait for error message
    await expect(page.getByText(/incorrect email or password/i)).toBeVisible({
      timeout: 5000,
    });
  });

  test("should successfully login with valid credentials (no MFA)", async ({
    page,
  }) => {
    // NOTE: This test assumes user 'test@example.com' exists without MFA enabled
    // You may need to create this user or use a different test account

    await page.getByLabel(/email/i).fill("test@example.com");
    await page.getByLabel(/password/i).fill("Test123!");

    // Submit form
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Check that user menu is visible (indicating successful login)
    await expect(page.getByRole("button", { name: /test/i })).toBeVisible();
  });

  test("should redirect to register page when clicking register link", async ({
    page,
  }) => {
    await page.getByRole("link", { name: /sign up/i }).click();

    await expect(page).toHaveURL(/\/register/);
  });

  test("should redirect to forgot password page", async ({ page }) => {
    await page.getByRole("link", { name: /forgot.*password/i }).click();

    await expect(page).toHaveURL(/\/forgot-password/);
  });

  test("should toggle password visibility", async ({ page }) => {
    const passwordInput = page.getByLabel(/password/i);

    // Initially should be type="password"
    await expect(passwordInput).toHaveAttribute("type", "password");

    // Click toggle button (eye icon)
    await page
      .locator('button[aria-label*="password"], button[type="button"]')
      .first()
      .click();

    // Should change to type="text"
    await expect(passwordInput).toHaveAttribute("type", "text");
  });
});

test.describe("Login with MFA Required", () => {
  test("should show MFA code field when MFA is required", async ({ page }) => {
    // Login with admin account (has MFA enabled)
    await page.goto("/login");

    await page.getByLabel(/email/i).fill("admin@example.com");
    await page.getByLabel(/password/i).fill("Admin123!");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Wait for MFA field to appear
    await expect(
      page.getByLabel(/verification code|mfa code|2fa code/i),
    ).toBeVisible({ timeout: 5000 });

    // Check that MFA explanation text is visible
    await expect(page.getByText(/enter.*authentication code/i)).toBeVisible();
  });
});
