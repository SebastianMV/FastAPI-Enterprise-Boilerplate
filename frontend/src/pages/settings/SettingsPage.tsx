import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { useConfigStore } from '@/stores/configStore';
import { useDarkMode } from '@/hooks/useDarkMode';
import { usersService } from '@/services/api';
import { ConfirmModal, AlertModal } from '@/components/common/Modal';
import { SUPPORTED_LANGUAGES } from '@/i18n';
import {
  Bell,
  Shield,
  Palette,
  Globe,
  Trash2,
  Moon,
  Sun,
  Check,
  Wifi,
  Monitor,
  Key,
  ChevronRight,
} from 'lucide-react';

/**
 * Settings page component.
 */
export default function SettingsPage() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { websocket_enabled, websocket_notifications } = useConfigStore();
  const { theme, setTheme } = useDarkMode();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: 'success' | 'error';
  }>({ isOpen: false, title: '', message: '', variant: 'success' });

  // UI preferences — non-sensitive, persist across sessions via localStorage.
  // Language is managed by i18next ('i18nextLng' key).
  const [notificationsEnabled, setNotificationsEnabled] = useState(() => {
    const stored = localStorage.getItem('notificationsEnabled');
    return stored !== null ? stored === 'true' : true;
  });
  const [timezone, setTimezone] = useState(() => {
    const stored = localStorage.getItem('timezone');
    return stored || 'America/Santiago';
  });

  // Delete account mutation
  const deleteAccountMutation = useMutation({
    mutationFn: () => {
      if (!user?.id) throw new Error('No user ID');
      return usersService.delete(user.id);
    },
    onSuccess: () => {
      setShowDeleteModal(false);
      logout();
      navigate('/login');
    },
    onError: (error: Error) => {
      setShowDeleteModal(false);
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('settings.deleteError'),
        variant: 'error',
      });
    },
  });

  const handleDeleteAccount = () => {
    deleteAccountMutation.mutate();
  };

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    setAlertModal({
      isOpen: true,
      title: t('settings.themeUpdated'),
      message: t('settings.themeChangedTo', { theme: newTheme }),
      variant: 'success',
    });
  };

  const handleNotificationToggle = () => {
    const newValue = !notificationsEnabled;
    setNotificationsEnabled(newValue);
    localStorage.setItem('notificationsEnabled', String(newValue));
    setAlertModal({
      isOpen: true,
      title: t('settings.notificationsUpdated'),
      message: t('settings.notificationsToggled', { status: newValue ? t('settings.enabled').toLowerCase() : t('settings.disabled').toLowerCase() }),
      variant: 'success',
    });
  };

  const handleLanguageChange = (newLanguage: string) => {
    i18n.changeLanguage(newLanguage);
    localStorage.setItem('i18nextLng', newLanguage);
    const langName = SUPPORTED_LANGUAGES.find(l => l.code === newLanguage)?.name || newLanguage;
    
    // Force re-render and show success message
    setTimeout(() => {
      setAlertModal({
        isOpen: true,
        title: t('common.success'),
        message: `${t('settings.language')}: ${langName}`,
        variant: 'success',
      });
    }, 100);
  };

  const handleTimezoneChange = (newTimezone: string) => {
    setTimezone(newTimezone);
    localStorage.setItem('timezone', newTimezone);
    setAlertModal({
      isOpen: true,
      title: t('settings.timezoneUpdated'),
      message: t('settings.timezoneChangedTo', { timezone: newTimezone }),
      variant: 'success',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          {t('settings.title')}
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          {t('settings.description')}
        </p>
      </div>

      {/* Profile card */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center">
              <span className="text-white text-xl font-bold">
                {user?.first_name?.charAt(0)}
              </span>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {user?.first_name} {user?.last_name}
              </h2>
              <p className="text-slate-500 dark:text-slate-400">{user?.email}</p>
              <p className="text-sm text-primary-600 dark:text-primary-400 mt-1">
                {user?.is_superuser ? t('settings.administrator') : t('settings.user')}
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/profile')}
            className="btn-secondary"
          >
            {t('profile.editProfile')}
          </button>
        </div>
      </div>

      {/* Notifications section */}
      <div className="card">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
              <Bell className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {t('settings.notifications')}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('settings.notificationPreferences')}
              </p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white">
                {t('settings.emailNotifications')}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('settings.emailNotificationsDescription')}
              </p>
            </div>
            <button
              onClick={handleNotificationToggle}
              role="switch"
              aria-checked={notificationsEnabled}
              aria-label={t('settings.emailNotifications')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                notificationsEnabled ? 'bg-primary-600' : 'bg-slate-300 dark:bg-slate-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  notificationsEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Appearance section */}
      <div className="card">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
              <Palette className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {t('settings.appearance')}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('settings.appearanceDescription')}
              </p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center space-x-3">
            {[
              { value: 'light', icon: Sun, label: t('settings.lightMode') },
              { value: 'dark', icon: Moon, label: t('settings.darkMode') },
              { value: 'system', icon: Monitor, label: t('settings.systemTheme') },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => handleThemeChange(option.value as 'light' | 'dark' | 'system')}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                  theme === option.value
                    ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                    : 'border-slate-200 dark:border-slate-700 hover:border-primary-300 text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800'
                }`}
              >
                <option.icon className="w-4 h-4" />
                <span className="text-sm font-medium">{option.label}</span>
                {theme === option.value && <Check className="w-4 h-4" />}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Language section */}
      <div className="card">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
              <Globe className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {t('settings.languageRegion')}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('settings.languageRegionDescription')}
              </p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                {t('settings.language')}
              </label>
              <select
                value={i18n.language}
                onChange={(e) => handleLanguageChange(e.target.value)}
                className="input"
              >
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.flag} {lang.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                {t('settings.timezone')}
              </label>
              <select 
                className="input" 
                value={timezone}
                onChange={(e) => handleTimezoneChange(e.target.value)}
              >
                <option value="America/Santiago">America/Santiago (GMT-4)</option>
                <option value="America/New_York">America/New_York (GMT-5)</option>
                <option value="America/Los_Angeles">America/Los_Angeles (GMT-8)</option>
                <option value="Europe/London">Europe/London (GMT)</option>
                <option value="Europe/Madrid">Europe/Madrid (GMT+1)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Features section (Read-only - configured via environment variables) */}
      <div className="card">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
              <Wifi className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {t('settings.features')}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('settings.featuresDescription')}
              </p>
            </div>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg">
                <Wifi className="w-4 h-4 text-slate-600 dark:text-slate-400" />
              </div>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-white">
                  {t('settings.websocketConnection')}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t('settings.websocketDescription')}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-medium ${websocket_enabled ? 'text-green-600' : 'text-slate-400'}`}>
                {websocket_enabled ? t('settings.enabled') : t('settings.disabled')}
              </span>
              <div className={`w-2 h-2 rounded-full ${websocket_enabled ? 'bg-green-500' : 'bg-slate-300'}`} />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg">
                <Bell className="w-4 h-4 text-slate-600 dark:text-slate-400" />
              </div>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-white">
                  {t('settings.realtimeNotifications')}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t('settings.realtimeNotificationsDescription')}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-medium ${websocket_notifications ? 'text-green-600' : 'text-slate-400'}`}>
                {websocket_notifications ? t('settings.enabled') : t('settings.disabled')}
              </span>
              <div className={`w-2 h-2 rounded-full ${websocket_notifications ? 'bg-green-500' : 'bg-slate-300'}`} />
            </div>
          </div>

          <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              <strong>{t('common.note')}:</strong> {t('settings.featuresNote')}
            </p>
          </div>
        </div>
      </div>

      {/* Security section */}
      <div className="card">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
              <Shield className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {t('settings.security')}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('settings.securityDescription')}
              </p>
            </div>
          </div>
        </div>
        <div className="divide-y divide-slate-200 dark:divide-slate-700">
          <button
            onClick={() => navigate('/security/mfa')}
            className="w-full p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <Key className="w-5 h-5 text-slate-500" />
              <div className="text-left">
                <h3 className="font-medium text-slate-900 dark:text-white">
                  {t('settings.twoFactorAuth')}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t('settings.twoFactorAuthDescription')}
                </p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-400" />
          </button>
          <button
            onClick={() => navigate('/security/sessions')}
            className="w-full p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <Monitor className="w-5 h-5 text-slate-500" />
              <div className="text-left">
                <h3 className="font-medium text-slate-900 dark:text-white">
                  {t('settings.activeSessions')}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t('settings.activeSessionsDescription')}
                </p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-400" />
          </button>
        </div>
      </div>

      {/* Danger zone */}
      <div className="card border-red-200 dark:border-red-800">
        <div className="p-6 border-b border-red-200 dark:border-red-800">
          <h2 className="text-lg font-semibold text-red-600 dark:text-red-400">
            {t('settings.dangerZone')}
          </h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white">
                {t('settings.deleteAccount')}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {t('settings.deleteAccountDescription')}
              </p>
            </div>
            <button
              onClick={() => setShowDeleteModal(true)}
              className="btn-danger"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              {t('settings.deleteAccount')}
            </button>
          </div>
        </div>
      </div>

      {/* Delete Account Confirmation Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteAccount}
        title={t('settings.deleteAccount')}
        message={t('settings.deleteAccountWarning')}
        confirmText={deleteAccountMutation.isPending ? t('settings.deletingAccount') : t('settings.deleteAccount')}
        cancelText={t('common.cancel')}
        variant="danger"
        isLoading={deleteAccountMutation.isPending}
      />

      {/* Alert Modal */}
      <AlertModal
        isOpen={alertModal.isOpen}
        onClose={() => setAlertModal({ ...alertModal, isOpen: false })}
        title={alertModal.title}
        message={alertModal.message}
        variant={alertModal.variant}
      />
    </div>
  );
}
