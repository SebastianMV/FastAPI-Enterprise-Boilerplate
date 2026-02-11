# 🌍 i18n Directory

> Internationalization configuration and translation files for the application

---

## 📁 Structure

```plaintext
src/i18n/
├── index.ts           # i18n configuration (react-i18next)
├── README.md          # This file
└── locales/           # Translation files
    ├── en.json        # English (source/fallback)
    ├── es.json        # Spanish
    └── pt.json        # Portuguese
```

---

## 🚀 Quick Start

### Using in Components

```typescript
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  
  return (
    <div>
      <h1>{t('common.title')}</h1>
      <p>{t('common.description')}</p>
    </div>
  );
}
```

### Changing Language

```typescript
import { useTranslation } from 'react-i18next';

function LanguageSwitcher() {
  const { i18n } = useTranslation();
  
  return (
    <button onClick={() => i18n.changeLanguage('es')}>
      Cambiar a Español
    </button>
  );
}
```

---

## 📊 Current Status

| Metric | Value |
| ------ | ----- |
| **Coverage** | 100% (all pages translated) |
| **Languages** | 3 (EN, ES, PT) |
| **Translation Keys** | ~700 per language |
| **Loading Strategy** | Lazy loading (optimized) |

---

## 🔑 Available Namespaces

All translations are in a single `translation` namespace:

- `common.*` - Shared UI elements
- `auth.*` - Authentication flows
- `navigation.*` - Navigation menu
- `dashboard.*` - Dashboard page
- `users.*` - User management
- `roles.*` - Role management
- `profile.*` - User profile
- `settings.*` - Settings page
- `apiKeys.*` - API Keys management
- `notifications.*` - Notifications
- `sessions.*` - Session management
- `mfa.*` - Two-factor authentication
- `tenants.*` - Tenant management
- `search.*` - Search functionality
- `oauth.*` - OAuth/SSO
- `audit.*` - Audit logs
- `validation.*` - Form validation
- `errors.*` - Error messages

---

## 📖 Documentation

For comprehensive documentation, see:

### **[📘 Complete i18n Guide](/docs/I18N.md)**

Topics covered:

- ✅ Adding new translations
- ✅ Translation key conventions
- ✅ Parameterization & pluralization
- ✅ Adding new languages
- ✅ Best practices
- ✅ Performance optimization
- ✅ Troubleshooting

---

## 🎯 Common Patterns

### Simple Translation

```typescript
t('common.save') // → "Save"
```

### With Parameters

```typescript
t('users.welcome', { name: 'John' })
// → "Welcome back, John!"
```

### Pluralization

```typescript
t('notifications.unreadCount', { count: 5 })
// → "You have 5 unread notifications"
```

### Dynamic Keys

```typescript
const plan = "professional";
t(`tenants.plans.${plan}`)
// → "Professional"
```

---

## 🌐 Supported Languages

### Active

- 🇺🇸 **English (en)** - Default
- 🇪🇸 **Español (es)** - Complete
- 🇧🇷 **Português (pt)** - Complete

---

## ⚙️ Configuration

The i18n system is configured in [index.ts](./index.ts) with:

- ✅ **Lazy Loading:** Translations loaded on-demand
- ✅ **Language Detection:** Auto-detect from browser/localStorage
- ✅ **Code Splitting:** Reduced bundle size (~150KB savings)
- ✅ **Preloading:** EN & ES preloaded for common users
- ✅ **Suspense:** React Suspense integration

---

## 🔧 Adding Translations

1. Edit `locales/en.json` (add English key)
2. Edit `locales/es.json` (add Spanish translation)
3. Repeat for PT, FR, DE
4. Copy to `public/locales/` for lazy loading
5. Use in component: `t('your.new.key')`

**Example:**

```json
// locales/en.json
{
  "myFeature": {
    "title": "My Feature",
    "action": "Click Me"
  }
}
```

```typescript
// Component
const { t } = useTranslation();
<h1>{t('myFeature.title')}</h1>
```

See [docs/I18N.md](/docs/I18N.md) for detailed guide.

---

## 🐛 Troubleshooting

### Translation not showing?

- Check key exists in JSON file
- Verify JSON syntax (no trailing commas)
- Check for typos in key name

### Parameterization not working?

```typescript
// ❌ Wrong
t('welcome', name: 'John')

// ✅ Correct
t('welcome', { name: 'John' })
```

### Language not switching?

```typescript
const { i18n } = useTranslation();
i18n.changeLanguage('es'); // Triggers re-render
```

---

## 📚 Resources

- **Full Documentation:** [/docs/I18N.md](/docs/I18N.md)
- **react-i18next:** [https://react.i18next.com/](https://react.i18next.com/)
- **i18next:** [https://www.i18next.com/](https://www.i18next.com/)
- **Examples:** All pages in `/src/pages/`

---

**Last Updated:** January 13, 2026  
**Maintained By:** FastAPI Enterprise Boilerplate Team
