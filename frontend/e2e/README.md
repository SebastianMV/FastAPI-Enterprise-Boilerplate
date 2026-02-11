# Playwright E2E Tests

Este directorio contiene los tests end-to-end (E2E) usando Playwright.

## 📁 Estructura

```text
e2e/
├── auth/
│   ├── login.spec.ts          # Login básico sin MFA
│   └── login-mfa.spec.ts      # Login con MFA habilitado
├── audit/
│   └── audit.spec.ts          # Audit logs y filtros
├── dashboard/
│   └── dashboard.spec.ts      # Dashboard principal y navegación
├── data/
│   └── data-exchange.spec.ts  # Import/Export de datos
├── notifications/
│   └── notifications.spec.ts  # Notificaciones y panel
├── profile/
│   └── profile.spec.ts        # Perfil de usuario y sesiones
├── roles/
│   └── roles.spec.ts          # Gestión de roles RBAC
├── search/
│   └── search.spec.ts         # Búsqueda global y resultados
├── security/
│   └── security.spec.ts       # MFA setup y configuración de seguridad
├── settings/
│   └── settings.spec.ts       # Página de configuración
├── users/
│   └── users.spec.ts          # Gestión de usuarios
└── README.md
```

## 🚀 Ejecutar Tests

### Ejecutar todos los tests

```bash
npm run test:e2e
```

### Modo interactivo con UI

```bash
npm run test:e2e:ui
```

### Modo visible (headed)

```bash
npm run test:e2e:headed
```

### Modo debug

```bash
npm run test:e2e:debug
```

### Ver reporte HTML

```bash
npm run test:e2e:report
```

## 📝 Comandos Disponibles

- `npm run test:e2e` - Ejecuta tests en modo headless
- `npm run test:e2e:ui` - Abre la UI de Playwright con modo watch
- `npm run test:e2e:headed` - Ejecuta tests con el navegador visible
- `npm run test:e2e:debug` - Ejecuta tests en modo debug paso a paso
- `npm run test:e2e:report` - Muestra el reporte HTML de la última ejecución

## 🔧 Configuración

La configuración se encuentra en `playwright.config.ts`:

- **baseURL**: `http://localhost:3000`
- **Browser**: Chromium (se puede agregar Firefox y WebKit)
- **Screenshots**: Solo en fallos
- **Videos**: Solo en fallos
- **Traces**: Solo en reintentos

## 📊 Cobertura Actual

### Tests Implementados (12 archivos, ~70 tests)

#### ✅ Auth - Login Básico (`login.spec.ts`)

- [x] Display login form
- [x] Validation for empty fields
- [x] Error for invalid credentials
- [x] Successful login without MFA
- [x] Navigate to register page
- [x] Navigate to forgot password
- [x] Toggle password visibility
- [x] Show MFA field when required

#### ✅ Auth - Login MFA (`login-mfa.spec.ts`)

- [x] Complete login with MFA code
- [x] Error for invalid MFA code
- [x] Validate 6-digit MFA code
- [x] Only accept numeric input
- [x] Show MFA field after password

#### ✅ Settings Page (`settings.spec.ts`)

- [x] Display all sections
- [x] **Theme buttons visible with contrast** ⚠️ Detecta bug arreglado
- [x] Theme buttons functional
- [x] Selected theme visually distinct
- [x] **Timezone selector functional** ⚠️ Detecta bug arreglado
- [x] Language selector functional
- [x] Notification toggle works
- [x] Navigate to profile page
- [x] Delete account confirmation modal
- [x] Features section read-only
- [x] **Dark mode theme buttons visible** ⚠️ Test específico del bug

#### ✅ Roles Page (`roles.spec.ts`)

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

#### ✅ Search Page (`search.spec.ts`)

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

#### ✅ Users Page (`users.spec.ts`)

- [x] Display users page with header
- [x] Show users table/list
- [x] Display user data columns
- [x] Search users
- [x] Action buttons for users
- [x] Paginate users
- [x] Show user count
- [x] View user details

#### ✅ Notifications (`notifications.spec.ts`)

- [x] Display notifications page
- [x] Show notification list or empty state
- [x] Mark all as read button
- [x] Filter notifications
- [x] Notification bell in header
- [x] Show dropdown on click
- [x] Notification count badge

#### ✅ Dashboard (`dashboard.spec.ts`)

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

#### ✅ Profile (`profile.spec.ts`)

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

#### ✅ Audit Logs (`audit.spec.ts`)

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

#### ✅ Data Exchange (`data-exchange.spec.ts`)

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

#### ✅ Security/MFA (`security.spec.ts`)

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

## 📖 Guía de Escritura de Tests

### Patrón AAA (Arrange, Act, Assert)

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

### Selectores Recomendados (en orden de preferencia)

1. **Role-based**: `page.getByRole('button', { name: /submit/i })`
2. **Label**: `page.getByLabel(/email/i)`
3. **Placeholder**: `page.getByPlaceholder(/enter email/i)`
4. **Text**: `page.getByText(/welcome/i)`
5. **Test ID**: `page.getByTestId('login-form')` (último recurso)

### Esperas Recomendadas

```typescript
// ✅ Bueno: Espera automática de Playwright
await expect(element).toBeVisible();

// ⚠️ Evitar: Espera fija (frágil)
await page.waitForTimeout(3000);

// ✅ Bueno: Espera condicional
await page.waitForURL(/\/dashboard/);
```

## 🐛 Tests que Detectan Bugs Arreglados

Los siguientes tests **habrían detectado automáticamente** los bugs que arreglamos manualmente:

### 1. Botones de Appearance no visibles (Dark Mode)

**Test**: `e2e/settings/settings.spec.ts` → "theme buttons are visible in dark mode"

```typescript
// Este test falla si los botones no tienen color de texto en dark mode
const lightBtnColor = await lightBtn.evaluate((el) => {
  return window.getComputedStyle(el).color;
});
expect(lightBtnColor).not.toBe('rgb(0, 0, 0)'); // ❌ Fallaría antes del fix
```

### 2. Timezone selector no funcional

**Test**: `e2e/settings/settings.spec.ts` → "timezone selector is functional"

```typescript
// Este test falla si el selector no tiene onChange handler
await timezoneSelect.selectOption('Europe/Madrid');
const savedTimezone = await page.evaluate(() => localStorage.getItem('timezone'));
expect(savedTimezone).toBe('Europe/Madrid'); // ❌ Fallaría antes del fix
```

## 🔄 CI/CD Integration

Para agregar a `.github/workflows/frontend.yml`:

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

## 💡 Tips

- Ejecuta `npm run test:e2e:ui` para modo visual interactivo
- Los tests reintentan automáticamente 2 veces en CI
- Screenshots y videos se guardan solo en fallos
- Usa `test.only()` para ejecutar un solo test durante desarrollo
- Usa `test.skip()` para deshabilitar temporalmente un test

## 📚 Recursos

- [Playwright Docs](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging](https://playwright.dev/docs/debug)
- [Selectors](https://playwright.dev/docs/selectors)
