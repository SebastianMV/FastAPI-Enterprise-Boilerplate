/**
 * Connected Accounts component for OAuth provider management.
 * 
 * Displays linked OAuth providers and allows users to connect/disconnect accounts.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Link2, 
  Unlink, 
  Loader2, 
  CheckCircle, 
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import { oauthService, type OAuthConnection } from '@/services/api';

// Display configuration for OAuth providers — NOT the same as OAUTH_PROVIDERS from oauthService.ts.
// This has JSX icons and Tailwind classes for the profile UI; oauthService has string IDs for API calls.
const PROVIDER_DISPLAY_CONFIG = [
  {
    id: 'google',
    name: 'Google',
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
    ),
    color: 'hover:bg-slate-100 dark:hover:bg-slate-700',
  },
  {
    id: 'github',
    name: 'GitHub',
    icon: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd"/>
      </svg>
    ),
    color: 'hover:bg-slate-100 dark:hover:bg-slate-700',
  },
  {
    id: 'microsoft',
    name: 'Microsoft',
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24">
        <path fill="#F25022" d="M1 1h10v10H1z"/>
        <path fill="#00A4EF" d="M1 13h10v10H1z"/>
        <path fill="#7FBA00" d="M13 1h10v10H13z"/>
        <path fill="#FFB900" d="M13 13h10v10H13z"/>
      </svg>
    ),
    color: 'hover:bg-slate-100 dark:hover:bg-slate-700',
  },
];

/**
 * Connected Accounts component.
 * Shows OAuth connections and allows linking/unlinking providers.
 */
export default function ConnectedAccounts() {
  const { t } = useTranslation();
  const [connections, setConnections] = useState<OAuthConnection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Fetch current connections on mount
  const fetchConnections = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await oauthService.getConnections();
      setConnections(data);
    } catch {
      // Don't show error for 404 (no connections yet)
      setConnections([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  const handleConnect = async (provider: string) => {
    try {
      setActionLoading(provider);
      setError(null);
      await oauthService.linkProvider(provider);
      // Redirect happens automatically
    } catch {
      setError(t('profile.connectError'));
      setActionLoading(null);
    }
  };

  const handleDisconnect = async (provider: string) => {
    try {
      setActionLoading(provider);
      setError(null);
      await oauthService.disconnect(provider);
      setConnections(connections.filter(c => c.provider !== provider));
      setSuccess(t('profile.disconnectSuccess', { provider: provider.charAt(0).toUpperCase() + provider.slice(1) }));
      setTimeout(() => setSuccess(null), 3000);
    } catch {
      setError(t('profile.disconnectError'));
    } finally {
      setActionLoading(null);
    }
  };

  const isConnected = (providerId: string) => {
    return connections.some(c => c.provider === providerId);
  };

  const getConnection = (providerId: string) => {
    return connections.find(c => c.provider === providerId);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
          {t('profile.connectedAccounts')}
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {t('profile.connectedAccountsDescription')}
        </p>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {success && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center space-x-3">
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
          <p className="text-sm text-green-700 dark:text-green-300">{success}</p>
        </div>
      )}

      {/* Provider List */}
      <div className="space-y-3">
        {PROVIDER_DISPLAY_CONFIG.map((provider) => {
          const connected = isConnected(provider.id);
          const connection = getConnection(provider.id);
          const loading = actionLoading === provider.id;

          return (
            <div
              key={provider.id}
              className={`flex items-center justify-between p-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg ${provider.color}`}
            >
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                  {provider.icon}
                </div>
                <div>
                  <h4 className="text-sm font-medium text-slate-900 dark:text-white">
                    {provider.name}
                  </h4>
                  {connected && connection ? (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {t('profile.connectedAs', { account: connection.provider_email || connection.provider_username || t('profile.connected') })}
                    </p>
                  ) : (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {t('profile.notConnected')}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {connected ? (
                  <button
                    onClick={() => handleDisconnect(provider.id)}
                    disabled={loading}
                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50 transition-colors"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                    ) : (
                      <Unlink className="w-4 h-4 mr-1.5" />
                    )}
                    {t('profile.disconnect')}
                  </button>
                ) : (
                  <button
                    onClick={() => handleConnect(provider.id)}
                    disabled={loading}
                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-900/40 disabled:opacity-50 transition-colors"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                    ) : (
                      <Link2 className="w-4 h-4 mr-1.5" />
                    )}
                    {t('profile.connect')}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Info Box */}
      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <div className="flex items-start space-x-3">
          <ExternalLink className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-700 dark:text-blue-300">
            <p className="font-medium">{t('profile.whyConnect')}</p>
            <ul className="mt-1 list-disc list-inside space-y-0.5 text-blue-600 dark:text-blue-400">
              <li>{t('profile.whyConnectReasons.faster')}</li>
              <li>{t('profile.whyConnectReasons.noPassword')}</li>
              <li>{t('profile.whyConnectReasons.sync')}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
