# Playwright E2E Tests

This directory contains end-to-end (E2E) tests using Playwright.

## Structure

```text
e2e/
├── auth/
│   ├── login.spec.ts          # Basic login without MFA
│   └── login-mfa.spec.ts      # Login with MFA enabled
├── audit/
│   └── audit.spec.ts          # Audit logs and filters
├── dashboard/
│   └── dashboard.spec.ts      # Main dashboard and navigation
├── data/
│   └── data-exchange.spec.ts  # Data import/export
├── notifications/
│   └── notifications.spec.ts  # Notifications and panel
├── profile/
│   └── profile.spec.ts        # User profile and sessions
├── roles/
│   └── roles.spec.ts          # RBAC role management
├── search/
│   └── search.spec.ts         # Global search and results
├── security/
│   └── security.spec.ts       # MFA setup and security settings
├── settings/
│   └── settings.spec.ts       # Settings page
├── users/
│   └── users.spec.ts          # User management
└── README.md
```

## Running Tests

### Run all tests

```bash
npm run test:e2e
```

### Interactive mode with UI

```bash
npm run test:e2e:ui
```

### Headed mode (visible browser)

```bash
npm run test:e2e:headed
```

### Debug mode

```bash
npm run test:e2e:debug
```

### View HTML report

```bash
npm run test:e2e:report
```

## Available Commands

- `npm run test:e2e` - Run tests in headless mode
- `npm run test:e2e:ui` - Open Playwright UI with watch mode
- `npm run test:e2e:headed` - Run tests with visible browser
- `npm run test:e2e:debug` - Run tests in step-by-step debug mode
- `npm run test:e2e:report` - Show HTML report from last run

## Configuration

Configuration is in `playwright.config.ts`:

- **baseURL**: `http://localhost:3000`
- **Browser**: Chromium (Firefox and WebKit can be added)
- **Screenshots**: On failure only
- **Videos**: On failure only
- **Traces**: On retries only

## Current Coverage

### Implemented Tests (12 files, ~70 tests)

#### Auth - Basic Login (`login.spec.ts`)

- [x] Display login form
- [x] Validation for empty fields
- [x] Error for invalid credentials
- [x] Successful login without MFA
- [x] Navigate to register page
- [x] Navigate to forgot password
- [x] Toggle password visibility
- [x] Show MFA field when required

#### Auth - Login MFA (`login-mfa.spec.ts`)

- [x] Complete login with MFA code
- [x] Error for invalid MFA code
- [x] Validate 6-digit MFA code
- [x] Only accept numeric input
- [x] Show MFA field after password

#### Settings Page (`settings.spec.ts`)

- [x] Display all sections
- [x] Theme buttons visible with contrast (detects fixed bug)
- [x] Theme buttons functional
- [x] Selected theme visually distinct
- [x] Timezone selector functional (detects fixed bug)
- [x] Language selector functional
- [x] Notification toggle works
- [x] Navigate to profile page
- [x] Delete account confirmation modal
- [x] Features section read-only
- [x] Dark mode theme buttons visible (bug-specific test)

#### Roles Page (`roles.spec.ts`)

- [x] Display roles page with header
- [x] Show roles table/list
- [x] Display default roles (admin)
- [x] Create role button visible
- [x] Open create role modal/form
- [x] Validate required fields
- [x] Create a new role
- [x] Show role permissions section
- [x] Edit functionality for roles
- [x] Delete functionality (non-system roles)
- [x] Confirm before deleting
- [x] Search/filter roles
- [x] Display role count/pagination
- [x] Redirect non-admin users

#### Search Page (`search.spec.ts`)

- [x] Display search bar in header
- [x] Focus on click
- [x] Show suggestions on typing
- [x] Navigate to search page on Enter
- [x] Clear search input
- [x] Close dropdown on Escape
- [x] Display search results
- [x] Filter by type
- [x] Result count
- [x] Pagination
- [x] Recent searches save
- [x] Display recent searches
- [x] Keyboard navigation
- [x] Accessibility labels

#### Users Page (`users.spec.ts`)

- [x] Display users page with header
- [x] Show users table/list
- [x] Display user data columns
- [x] Search users
- [x] Action buttons for users
- [x] Paginate users
- [x] Show user count
- [x] View user details

#### Notifications (`notifications.spec.ts`)

- [x] Display notifications page
- [x] Show notification list or empty state
- [x] Mark all as read button
- [x] Filter notifications
- [x] Notification bell in header
- [x] Show dropdown on click
- [x] Notification count badge

#### Dashboard (`dashboard.spec.ts`)

- [x] Display dashboard page
- [x] Show welcome message or user info
- [x] Display statistics cards
- [x] Navigation sidebar/menu
- [x] User menu in header
- [x] Navigate to users page
- [x] Navigate to roles page
- [x] Navigate to settings
- [x] Logout successfully
- [x] Responsive on mobile viewport
- [x] Quick action buttons

#### Profile (`profile.spec.ts`)

- [x] Display profile page
- [x] Show user information
- [x] Display avatar/placeholder
- [x] Edit profile button/form
- [x] First/last name fields
- [x] Update profile successfully
- [x] Validate required fields
- [x] Change password section
- [x] Password form fields
- [x] Navigate to sessions
- [x] Show current session

#### Audit Logs (`audit.spec.ts`)

- [x] Display audit logs page
- [x] Show logs table/list
- [x] Display action types
- [x] Filter options
- [x] Filter by action type
- [x] Pagination
- [x] Log details on click
- [x] Export functionality
- [x] Timestamps display
- [x] Actor/user display
- [x] Access control for non-admin

#### Data Exchange (`data-exchange.spec.ts`)

- [x] Display data exchange page
- [x] Export section
- [x] Import section
- [x] Entity type selector
- [x] Format selector for export
- [x] Trigger export download
- [x] Download template option
- [x] File upload zone
- [x] Accept CSV/Excel files
- [x] Validation mode option
- [x] Import/export history

#### Security/MFA (`security.spec.ts`)

- [x] Display security page
- [x] MFA status section
- [x] Enable MFA button
- [x] QR code display
- [x] Manual setup key
- [x] Code verification required
- [x] 6-digit code validation
- [x] Backup codes section
- [x] View backup codes
- [x] Disable MFA option
- [x] Password required to disable
- [x] Active sessions section
- [x] Sign out all sessions

## Test Writing Guide

### AAA Pattern (Arrange, Act, Assert)

```typescript
test('should do something', async ({ page }) => {
  // Arrange: Setup
  await page.goto('/some-page');

  // Act: Perform action
  await page.getByRole('button', { name: /click me/i }).click();

  // Assert: Verify result
  await expect(page.getByText('Success')).toBeVisible();
});
```

### Recommended Selectors (in order of preference)

1. **Role-based**: `page.getByRole('button', { name: /submit/i })`
2. **Label**: `page.getByLabel(/email/i)`
3. **Placeholder**: `page.getByPlaceholder(/enter email/i)`
4. **Text**: `page.getByText(/welcome/i)`
5. **Test ID**: `page.getByTestId('login-form')` (last resort)

### Recommended Waits

```typescript
// Good: Playwright auto-wait
await expect(element).toBeVisible();

// Avoid: Fixed wait (fragile)
await page.waitForTimeout(3000);

// Good: Conditional wait
await page.waitForURL(/\/dashboard/);
```

## Tests That Detect Fixed Bugs

The following tests **would have automatically detected** the bugs we fixed manually:

### 1. Appearance Buttons Not Visible (Dark Mode)

**Test**: `e2e/settings/settings.spec.ts` → "theme buttons are visible in dark mode"

```typescript
// This test fails if buttons have no text color in dark mode
const lightBtnColor = await lightBtn.evaluate((el) => {
  return window.getComputedStyle(el).color;
});
expect(lightBtnColor).not.toBe('rgb(0, 0, 0)'); // Would fail before the fix
```

### 2. Timezone Selector Not Functional

**Test**: `e2e/settings/settings.spec.ts` → "timezone selector is functional"

```typescript
// This test fails if the selector has no onChange handler
await timezoneSelect.selectOption('Europe/Madrid');
const savedTimezone = await page.evaluate(() => localStorage.getItem('timezone'));
expect(savedTimezone).toBe('Europe/Madrid'); // Would fail before the fix
```

## CI/CD Integration

To add to `.github/workflows/frontend.yml`:

```yaml
- name: Install Playwright Browsers
  run: npx playwright install --with-deps chromium

- name: Run E2E Tests
  run: npm run test:e2e

- name: Upload Test Report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Tips

- Run `npm run test:e2e:ui` for visual interactive mode
- Tests automatically retry 2 times in CI
- Screenshots and videos are saved only on failures
- Use `test.only()` to run a single test during development
- Use `test.skip()` to temporarily disable a test

## Resources

- [Playwright Docs](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging](https://playwright.dev/docs/debug)
- [Selectors](https://playwright.dev/docs/selectors)
