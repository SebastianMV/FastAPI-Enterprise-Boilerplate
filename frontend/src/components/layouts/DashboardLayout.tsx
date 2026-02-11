import { useState, useEffect, useRef } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { useConfigStore } from '@/stores/configStore';
import SearchBar from '@/components/common/SearchBar';
import NotificationsDropdown from '@/components/notifications/NotificationsDropdown';
import EmailVerificationBanner from '@/components/common/EmailVerificationBanner';
import {
  LayoutDashboard,
  Users,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronDown,
  User,
  Shield,
  Key,
  Globe,
  Bell,
  FileText,
  Building2,
  ArrowLeftRight,
} from 'lucide-react';

/**
 * Main dashboard layout with sidebar navigation.
 */
export default function DashboardLayout() {
  const { t } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { fetchFeatures } = useConfigStore();

  // Fetch feature config on mount
  useEffect(() => {
    fetchFeatures();
  }, [fetchFeatures]);

  // Close user menu on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [userMenuOpen]);

  // Build navigation based on enabled features
  const navigation = [
    { name: t('navigation.dashboard'), href: '/dashboard', icon: LayoutDashboard },
    { name: t('navigation.users'), href: '/users', icon: Users },
    { name: t('navigation.roles'), href: '/roles', icon: Shield },
    { name: t('navigation.notifications'), href: '/notifications', icon: Bell },
    { name: t('navigation.auditLog'), href: '/security/audit', icon: FileText },
    { name: t('navigation.settings'), href: '/settings', icon: Settings },
    // Superuser only
    ...(user?.is_superuser ? [
      { name: t('navigation.tenants'), href: '/admin/tenants', icon: Building2 },
      { name: t('navigation.dataExchange'), href: '/admin/data', icon: ArrowLeftRight },
    ] : []),
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          role="button"
          tabIndex={0}
          aria-label={t('common.close')}
          onClick={() => setSidebarOpen(false)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSidebarOpen(false); }}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 transform transition-transform duration-200 lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-slate-200 dark:border-slate-700">
          <Link to="/" className="flex items-center space-x-2">
            <img src="/logo.svg" alt={t('common.brandLogoAlt')} className="w-8 h-8" />
            <span className="font-semibold text-slate-900 dark:text-white">
              {t('common.brandName')}
            </span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 text-slate-500 hover:text-slate-700"
            aria-label={t('common.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top navbar */}
        <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 text-slate-500 hover:text-slate-700"
            aria-label={t('common.menu', 'Open menu')}
          >
            <Menu className="w-6 h-6" />
          </button>

          {/* Search bar - centered */}
          <div className="flex-1 max-w-xl mx-4 hidden md:block">
            <SearchBar />
          </div>

          {/* Right side: Notifications + User menu */}
          <div className="flex items-center gap-2">
            {/* Notifications */}
            <NotificationsDropdown />

            {/* User menu */}
            <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              aria-expanded={userMenuOpen}
              aria-haspopup="true"
              className="flex items-center space-x-2 p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">
                  {user?.first_name?.charAt(0) || 'U'}
                </span>
              </div>
              <span className="hidden md:block text-sm text-slate-700 dark:text-slate-300">
                {user?.first_name} {user?.last_name}
              </span>
              <ChevronDown className="w-4 h-4 text-slate-500" />
            </button>

            {/* Dropdown */}
            {userMenuOpen && (
              <div role="menu" aria-label={t('userMenu.title', 'User menu')} className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1">
                <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
                  <p className="text-sm font-medium text-slate-900 dark:text-white">
                    {user?.first_name} {user?.last_name}
                  </p>
                  <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                </div>
                
                {/* Profile & Account Links */}
                <div className="py-1">
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      navigate('/profile');
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    <User className="w-4 h-4" />
                    <span>{t('userMenu.myProfile')}</span>
                  </button>
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      navigate('/settings');
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    <Globe className="w-4 h-4" />
                    <span>{t('userMenu.languagePreferences')}</span>
                  </button>
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      navigate('/settings/api-keys');
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    <Key className="w-4 h-4" />
                    <span>{t('userMenu.apiKeys')}</span>
                  </button>
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      navigate('/security/mfa');
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    <Shield className="w-4 h-4" />
                    <span>{t('userMenu.security')}</span>
                  </button>
                </div>
                
                {/* Sign out */}
                <div className="border-t border-slate-200 dark:border-slate-700 py-1">
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>{t('common.signOut')}</span>
                  </button>
                </div>
              </div>
            )}
            </div>
          </div>
        </header>
        
        {/* Email verification banner */}
        <EmailVerificationBanner />

        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
