import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Roles Page
 * 
 * Tests role management functionality:
 * - Viewing roles list
 * - Creating new roles
 * - Editing roles
 * - Assigning permissions
 * - Deleting roles
 */

test.describe('Roles Page', () => {
  test.beforeEach(async ({ page }) => {
    // Login with admin/superuser credentials
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('admin@example.com');
    await page.getByLabel(/password/i).fill('Admin123!');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Wait for login and redirect
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    
    // Navigate to roles page
    await page.goto('/roles');
  });

  test('should display roles page with header', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /roles/i })).toBeVisible();
  });

  test('should show roles table or list', async ({ page }) => {
    // Wait for roles to load
    await page.waitForLoadState('networkidle');
    
    // Should have at least the default admin role
    const rolesContainer = page.locator('[data-testid="roles-list"], table, [role="table"]');
    await expect(rolesContainer).toBeVisible({ timeout: 10000 });
  });

  test('should display default roles', async ({ page }) => {
    // Wait for content to load
    await page.waitForLoadState('networkidle');
    
    // Common default roles that should exist
    const adminRole = page.getByText(/admin/i);
    await expect(adminRole.first()).toBeVisible({ timeout: 5000 });
  });

  test('should have create role button', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create|add|new/i });
    await expect(createButton).toBeVisible();
  });

  test('should open create role modal/form', async ({ page }) => {
    // Click create button
    const createButton = page.getByRole('button', { name: /create|add|new/i });
    await createButton.click();
    
    // Modal or form should appear
    const modal = page.getByRole('dialog');
    const form = page.locator('form');
    
    // Either modal or inline form should be visible
    const isModalVisible = await modal.isVisible().catch(() => false);
    const isFormVisible = await form.isVisible().catch(() => false);
    
    expect(isModalVisible || isFormVisible).toBe(true);
  });

  test('create role form should have name input', async ({ page }) => {
    // Click create button
    const createButton = page.getByRole('button', { name: /create|add|new/i });
    await createButton.click();
    
    // Check for name input
    const nameInput = page.getByLabel(/name/i);
    await expect(nameInput).toBeVisible({ timeout: 3000 });
  });

  test('should validate required fields on create', async ({ page }) => {
    // Click create button
    const createButton = page.getByRole('button', { name: /create|add|new/i });
    await createButton.click();
    
    // Try to submit empty form
    const submitButton = page.getByRole('button', { name: /save|create|submit/i });
    await submitButton.click();
    
    // Should show validation error or remain on form
    // Form should still be visible (not submitted)
    const form = page.locator('form');
    await expect(form).toBeVisible({ timeout: 2000 });
  });

  test('should be able to create a new role', async ({ page }) => {
    const uniqueRoleName = `TestRole_${Date.now()}`;
    
    // Click create button
    const createButton = page.getByRole('button', { name: /create|add|new/i });
    await createButton.click();
    
    // Fill in role name
    const nameInput = page.getByLabel(/name/i);
    await nameInput.fill(uniqueRoleName);
    
    // Optionally add description
    const descInput = page.getByLabel(/description/i);
    if (await descInput.isVisible()) {
      await descInput.fill('Test role created by E2E test');
    }
    
    // Submit
    const submitButton = page.getByRole('button', { name: /save|create|submit/i });
    await submitButton.click();
    
    // Wait for success (modal closes or success message)
    await page.waitForLoadState('networkidle');
    
    // New role should appear in list
    await expect(page.getByText(uniqueRoleName)).toBeVisible({ timeout: 5000 });
  });

  test('should show role permissions section', async ({ page }) => {
    // Wait for roles to load
    await page.waitForLoadState('networkidle');
    
    // Click on a role to view details
    const roleRow = page.getByText(/admin/i).first();
    await roleRow.click();
    
    // Wait for detail view
    await page.waitForTimeout(500);
    
    // Should see permissions section or checkboxes
    const permissionsSection = page.getByText(/permissions/i);
    const permissionCheckboxes = page.getByRole('checkbox');
    
    const hasPermissionsLabel = await permissionsSection.isVisible().catch(() => false);
    const hasCheckboxes = await permissionCheckboxes.first().isVisible().catch(() => false);
    
    // Either should be visible when viewing role details
    expect(hasPermissionsLabel || hasCheckboxes).toBe(true);
  });

  test('should have edit functionality for roles', async ({ page }) => {
    // Wait for roles to load
    await page.waitForLoadState('networkidle');
    
    // Look for edit button on any role row
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    
    // Edit button should exist
    await expect(editButton).toBeVisible({ timeout: 5000 });
  });

  test('should have delete functionality for non-system roles', async ({ page }) => {
    // Wait for roles to load
    await page.waitForLoadState('networkidle');
    
    // Look for delete button (may be disabled for system roles)
    const deleteButton = page.getByRole('button', { name: /delete|remove/i }).first();
    
    // Should have at least one delete button visible
    const isVisible = await deleteButton.isVisible().catch(() => false);
    
    // Note: System roles like 'admin' may have delete disabled
    // So we just check the button exists somewhere
    if (!isVisible) {
      // Check for icon-only delete buttons
      const trashIcon = page.locator('svg[class*="trash"], button[aria-label*="delete"]').first();
      await expect(trashIcon).toBeVisible();
    }
  });

  test('should confirm before deleting role', async ({ page }) => {
    // First create a test role to delete
    const uniqueRoleName = `DeleteMe_${Date.now()}`;
    
    const createButton = page.getByRole('button', { name: /create|add|new/i });
    await createButton.click();
    
    await page.getByLabel(/name/i).fill(uniqueRoleName);
    await page.getByRole('button', { name: /save|create|submit/i }).click();
    
    await page.waitForLoadState('networkidle');
    
    // Find the created role and its delete button
    const roleRow = page.getByText(uniqueRoleName);
    await expect(roleRow).toBeVisible({ timeout: 5000 });
    
    // Click on the row to select it or find delete in that row
    const deleteButton = page.getByRole('row', { name: new RegExp(uniqueRoleName, 'i') })
      .getByRole('button', { name: /delete|remove/i });
    
    if (await deleteButton.isVisible()) {
      await deleteButton.click();
      
      // Confirmation dialog should appear
      const confirmDialog = page.getByRole('alertdialog');
      const confirmButton = page.getByRole('button', { name: /confirm|yes|delete/i });
      
      const hasDialog = await confirmDialog.isVisible().catch(() => false);
      const hasConfirm = await confirmButton.isVisible().catch(() => false);
      
      expect(hasDialog || hasConfirm).toBe(true);
    }
  });

  test('should search/filter roles', async ({ page }) => {
    // Look for search input
    const searchInput = page.getByPlaceholder(/search|filter/i);
    
    if (await searchInput.isVisible()) {
      await searchInput.fill('admin');
      
      // Wait for filter to apply
      await page.waitForTimeout(500);
      
      // Admin role should still be visible
      await expect(page.getByText(/admin/i).first()).toBeVisible();
    }
  });

  test('should display role count or pagination', async ({ page }) => {
    // Wait for roles to load
    await page.waitForLoadState('networkidle');
    
    // Look for role count or pagination
    const countText = page.getByText(/\d+\s*(roles?|results?|items?)/i);
    const pagination = page.getByRole('navigation', { name: /pagination/i });
    const pageButtons = page.getByRole('button', { name: /\d+|next|previous/i });
    
    const hasCount = await countText.isVisible().catch(() => false);
    const hasPagination = await pagination.isVisible().catch(() => false);
    const hasPageButtons = await pageButtons.first().isVisible().catch(() => false);
    
    // At least one should be present for proper UX
    expect(hasCount || hasPagination || hasPageButtons).toBe(true);
  });
});

test.describe('Roles Page - Authorization', () => {
  test('should redirect non-admin users to unauthorized', async ({ page }) => {
    // Login as regular user
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('user@example.com');
    await page.getByLabel(/password/i).fill('User123!');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    
    // Try to access roles page
    await page.goto('/roles');
    
    // Should either redirect to unauthorized or show access denied
    const isUnauthorized = await page.getByText(/unauthorized|forbidden|access denied/i).isVisible().catch(() => false);
    const wasRedirected = page.url().includes('unauthorized') || page.url().includes('403') || !page.url().includes('roles');
    
    expect(isUnauthorized || wasRedirected).toBe(true);
  });
});
