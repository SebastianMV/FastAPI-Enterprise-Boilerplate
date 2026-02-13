import api, { OAUTH_PROVIDERS } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';

interface OAuthCallbackResult {
  is_new_user: boolean;
}

/**
 * OAuth callback page that handles the redirect from OAuth providers.
 *
 * Processes the authorization code and completes the authentication.
 */
export default function OAuthCallbackPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { fetchUser } = useAuthStore();

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState(t('oauth.processing'));
  const [isNewUser, setIsNewUser] = useState(false);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();

    const handleCallback = async () => {
      // Clean the OAuth code/state from the URL immediately
      window.history.replaceState({}, '', '/oauth/callback');

      // Get params from URL
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      // Handle OAuth error (don't trust error_description from URL)
      if (error) {
        setStatus('error');
        setMessage(t('oauth.authFailedGeneric'));
        return;
      }

      // Validate required params
      if (!code || !state) {
        setStatus('error');
        setMessage(t('oauth.invalidCallback'));
        return;
      }

      // Verify state against what we stored in sessionStorage (CSRF protection)
      // Fail-closed: reject if no stored state or if it doesn't match
      const storedState = sessionStorage.getItem('oauth_state');
      if (!storedState || storedState !== state) {
        setStatus('error');
        setMessage(t('oauth.invalidCallback'));
        return;
      }
      // Clean up stored state after verification
      sessionStorage.removeItem('oauth_state');

      try {
        // Extract provider from state (format: provider_randomstring)
        const provider = state.split('_')[0];

        // Validate provider against known allowlist to prevent path traversal
        if (!provider || !OAUTH_PROVIDERS.map(p => p.id).includes(provider)) {
          throw new Error(t('oauth.invalidState'));
        }

        // Complete OAuth flow
        const response = await api.get<OAuthCallbackResult>(
          `/auth/oauth/${encodeURIComponent(provider)}/callback`,
          {
            params: { code, state },
            signal: controller.signal,
          }
        );

        if (controller.signal.aborted) return;

        const { is_new_user } = response.data;

        // Tokens are set as HttpOnly cookies by the backend.
        // Fetch user profile to confirm authentication.
        await fetchUser();

        if (controller.signal.aborted) return;

        setIsNewUser(is_new_user);
        setStatus('success');
        setMessage(
          is_new_user
            ? t('oauth.accountCreated')
            : t('oauth.signedIn')
        );

        // Redirect after short delay
        timeoutId = setTimeout(() => {
          navigate(is_new_user ? '/profile' : '/dashboard', { replace: true });
        }, 1500);

      } catch {
        if (controller.signal.aborted) return;
        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console -- development-only error logging
          console.error('OAuth callback failed');
        }
        setStatus('error');
        setMessage(t('oauth.authFailedGeneric'));
      }
    };

    handleCallback();

    return () => {
      controller.abort();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [searchParams, navigate, fetchUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
      <div className="card p-8 max-w-md w-full text-center">
        {/* Status Icon */}
        <div className="mb-6">
          {status === 'loading' && (
            <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full">
              <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
            </div>
          )}
          {status === 'success' && (
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
          )}
          {status === 'error' && (
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full">
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
          )}
        </div>

        {/* Title */}
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
          {status === 'loading' && t('oauth.completingSignIn')}
          {status === 'success' && (isNewUser ? t('oauth.welcome') : t('oauth.welcomeBack'))}
          {status === 'error' && t('oauth.authFailed')}
        </h1>

        {/* Message */}
        <p className="text-slate-600 dark:text-slate-400 mb-6">
          {message}
        </p>

        {/* Actions */}
        {status === 'error' && (
          <div className="space-y-3">
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="btn-primary w-full"
            >
              {t('oauth.backToLogin')}
            </button>
          </div>
        )}

        {status === 'success' && (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('oauth.redirecting', {
              destination: isNewUser ? t('oauth.yourProfile') : t('oauth.theDashboard')
            })}
          </p>
        )}
      </div>
    </div>
  );
}
