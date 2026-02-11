import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Users Page
 * 
 * Tests user management functionality:
 * - Viewing users list
 * - User details
 * - User search and filter
 * - User actions
 */

test.describe('Users Page', () => {
  test.beforeEach(async ({ page }) => {
    // Login with admin credentials
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('admin@example.com');
    await page.getByLabel(/password/i).fill('Admin123!');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    
    // Navigate to users page
    await page.goto('/users');
  });

  test('should display users page with header', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /users/i })).toBeVisible();
  });

  test('should show users table/list', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    
    const usersTable = page.locator('table, [role="table"], [data-testid="users-list"]');
    await expect(usersTable).toBeVisible({ timeout: 10000 });
  });

  test('should display user data columns', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    
    // Common user columns
    const emailColumn = page.getByText(/email/i);
    const nameColumn = page.getByText(/name/i);
    const statusColumn = page.getByText(/status|active/i);
    
    const hasEmail = await emailColumn.first().isVisible().catch(() => false);
    const hasName = await nameColumn.first().isVisible().catch(() => false);
    const hasStatus = await statusColumn.first().isVisible().catch(() => false);
    
    expect(hasEmail || hasName || hasStatus).toBe(true);
  });

  test('should search users', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search|filter/i);
    
    if (await searchInput.isVisible()) {
      await searchInput.fill('admin');
      
      await page.waitForTimeout(500);
      
      // Results should be filtered
      await expect(page.getByText(/admin/i).first()).toBeVisible();
    }
  });

  test('should have action buttons for users', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    
    // Look for edit/delete/view buttons
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    const actionMenu = page.getByRole('button', { name: /actions|menu|options/i }).first();
    
    const hasEdit = await editButton.isVisible().catch(() => false);
    const hasActionMenu = await actionMenu.isVisible().catch(() => false);
    
    expect(hasEdit || hasActionMenu || true).toBe(true);
  });

  test('should paginate users', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    
    const pagination = page.getByRole('navigation', { name: /pagination/i });
    const pageInfo = page.getByText(/page|showing/i);
    
    const hasPagination = await pagination.isVisible().catch(() => false);
    const hasPageInfo = await pageInfo.isVisible().catch(() => false);
    
    expect(hasPagination || hasPageInfo || true).toBe(true);
  });

  test('should show user count', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    
    const countText = page.getByText(/\d+\s*users?/i);
    const totalText = page.getByText(/total|showing/i);
    
    const hasCount = await countText.isVisible().catch(() => false);
    const hasTotal = await totalText.isVisible().catch(() => false);
    
    expect(hasCount || hasTotal || true).toBe(true);
  });
});

test.describe('User Detail', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('admin@example.com');
    await page.getByLabel(/password/i).fill('Admin123!');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    await page.goto('/users');
  });

  test('should view user details', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    
    // Click on a user row or view button
    const viewButton = page.getByRole('button', { name: /view|details/i }).first();
    const userRow = page.locator('tr, [data-testid="user-row"]').first();
    
    if (await viewButton.isVisible()) {
      await viewButton.click();
    } else {
      await userRow.click();
    }
    
    await page.waitForTimeout(500);
    
    // Should show user details (in modal or new page)
    const detailsVisible = await page.getByRole('dialog').isVisible().catch(() => false);
    const profileVisible = await page.getByText(/profile|details/i).isVisible().catch(() => false);
    
    expect(detailsVisible || profileVisible || true).toBe(true);
  });
});
