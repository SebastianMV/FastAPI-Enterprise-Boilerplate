import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { useConfigStore } from '@/stores/configStore';
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
  const { i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { websocket_enabled, websocket_notifications } = useConfigStore();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: 'success' | 'error';
  }>({ isOpen: false, title: '', message: '', variant: 'success' });

  // Theme state - persisted in localStorage
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>(() => {
    const stored = localStorage.getItem('theme');
    return (stored as 'light' | 'dark' | 'system') || 'system';
  });
  const [notificationsEnabled, setNotificationsEnabled] = useState(() => {
    const stored = localStorage.getItem('notificationsEnabled');
    return stored !== null ? stored === 'true' : true;
  });
  const [timezone, setTimezone] = useState(() => {
    const stored = localStorage.getItem('timezone');
    return stored || 'America/Santiago';
  });

  // Apply theme on mount and when it changes
  useEffect(() => {
    const applyTheme = (selectedTheme: 'light' | 'dark' | 'system') => {
      if (selectedTheme === 'dark') {
        document.documentElement.classList.add('dark');
      } else if (selectedTheme === 'light') {
        document.documentElement.classList.remove('dark');
      } else {
        // System preference
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      }
    };
    applyTheme(theme);
  }, [theme]);

  // Delete account mutation
  const deleteAccountMutation = useMutation({
    mutationFn: () => usersService.delete(user?.id || ''),
    onSuccess: () => {
      setShowDeleteModal(false);
      logout();
      navigate('/login');
    },
    onError: (error: Error) => {
      setShowDeleteModal(false);
      setAlertModal({
        isOpen: true,
        title: 'Error',
        message: error.message || 'Failed to delete account. Please try again.',
        variant: 'error',
      });
    },
  });

  const handleDeleteAccount = () => {
    deleteAccountMutation.mutate();
  };

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    setAlertModal({
      isOpen: true,
      title: 'Theme Updated',
      message: `Theme changed to ${newTheme}.`,
      variant: 'success',
    });
  };

  const handleNotificationToggle = () => {
    const newValue = !notificationsEnabled;
    setNotificationsEnabled(newValue);
    localStorage.setItem('notificationsEnabled', String(newValue));
    setAlertModal({
      isOpen: true,
      title: 'Notifications Updated',
      message: `Notifications ${newValue ? 'enabled' : 'disabled'}.`,
      variant: 'success',
    });
  };

  const handleLanguageChange = (newLanguage: string) => {
    i18n.changeLanguage(newLanguage);
    const langName = SUPPORTED_LANGUAGES.find(l => l.code === newLanguage)?.name || newLanguage;
    setAlertModal({
      isOpen: true,
      title: 'Language Updated',
      message: `Language changed to ${langName}.`,
      variant: 'success',
    });
  };

  const handleTimezoneChange = (newTimezone: string) => {
    setTimezone(newTimezone);
    localStorage.setItem('timezone', newTimezone);
    setAlertModal({
      isOpen: true,
      title: 'Timezone Updated',
      message: `Timezone changed to ${newTimezone}.`,
      variant: 'success',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Settings
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Manage your account settings and preferences
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
                {user?.is_superuser ? 'Administrator' : 'User'}
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/profile')}
            className="btn-secondary"
          >
            Edit Profile
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
                Notifications
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Configure notification preferences
              </p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white">
                Email Notifications
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Receive email notifications for important updates
              </p>
            </div>
            <button
              onClick={handleNotificationToggle}
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
                Appearance
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Customize the look and feel
              </p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center space-x-3">
            {[
              { value: 'light', icon: Sun, label: 'Light' },
              { value: 'dark', icon: Moon, label: 'Dark' },
              { value: 'system', icon: Shield, label: 'System' },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => handleThemeChange(option.value as 'light' | 'dark' | 'system')}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                  theme === option.value
                    ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20 text-primary-600'
                    : 'border-slate-200 dark:border-slate-700 hover:border-primary-300'
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
                Language & Region
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Set your language and timezone
              </p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                Language
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
                Timezone
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
                Features
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Optional features configured by system administrator
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
                  WebSocket Connection
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Real-time bidirectional communication
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-medium ${websocket_enabled ? 'text-green-600' : 'text-slate-400'}`}>
                {websocket_enabled ? 'Enabled' : 'Disabled'}
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
                  Real-time Notifications
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Instant notification delivery via WebSocket
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-medium ${websocket_notifications ? 'text-green-600' : 'text-slate-400'}`}>
                {websocket_notifications ? 'Enabled' : 'Disabled'}
              </span>
              <div className={`w-2 h-2 rounded-full ${websocket_notifications ? 'bg-green-500' : 'bg-slate-300'}`} />
            </div>
          </div>

          <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              <strong>Note:</strong> These features are configured via environment variables by the system administrator. 
              Contact your administrator to enable or disable optional features.
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
                Security
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Manage your account security settings
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
                  Two-Factor Authentication
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Add an extra layer of security to your account
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
                  Active Sessions
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  View and manage your active sessions across devices
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
            Danger Zone
          </h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white">
                Delete Account
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Delete your account. This uses soft delete and can be reversed by an administrator.
              </p>
            </div>
            <button
              onClick={() => setShowDeleteModal(true)}
              className="btn-danger"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Account
            </button>
          </div>
        </div>
      </div>

      {/* Delete Account Confirmation Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteAccount}
        title="Delete Account"
        message="Are you sure you want to delete your account? This action uses soft delete and can be reversed by an administrator. You will be logged out immediately."
        confirmText={deleteAccountMutation.isPending ? 'Deleting...' : 'Delete Account'}
        cancelText="Cancel"
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
