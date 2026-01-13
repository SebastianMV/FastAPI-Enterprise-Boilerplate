import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import api from '@/services/api';

interface OAuthCallbackResult {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
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
  const { setTokens, fetchUser } = useAuthStore();
  
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState(t('oauth.processing'));
  const [isNewUser, setIsNewUser] = useState(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Get params from URL
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Handle OAuth error
      if (error) {
        setStatus('error');
        setMessage(errorDescription || t('oauth.authError', { error }));
        return;
      }

      // Validate required params
      if (!code || !state) {
        setStatus('error');
        setMessage(t('oauth.invalidCallback'));
        return;
      }

      try {
        // Extract provider from state (format: provider_randomstring)
        const provider = state.split('_')[0];
        
        if (!provider) {
          throw new Error(t('oauth.invalidState'));
        }

        // Complete OAuth flow
        const response = await api.get<OAuthCallbackResult>(
          `/auth/oauth/${provider}/callback`,
          {
            params: { code, state },
          }
        );

        const { access_token, refresh_token, is_new_user } = response.data;

        // Store tokens
        setTokens(access_token, refresh_token);
        
        // Fetch user data
        await fetchUser();

        setIsNewUser(is_new_user);
        setStatus('success');
        setMessage(
          is_new_user 
            ? t('oauth.accountCreated') 
            : t('oauth.signedIn')
        );

        // Redirect after short delay
        setTimeout(() => {
          navigate(is_new_user ? '/profile' : '/dashboard', { replace: true });
        }, 1500);

      } catch (error) {
        console.error('OAuth callback error:', error);
        setStatus('error');
        
        if (error instanceof Error) {
          setMessage(error.message);
        } else {
          setMessage(t('oauth.authFailedGeneric'));
        }
      }
    };

    handleCallback();
  }, [searchParams, navigate, setTokens, fetchUser]);

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
              onClick={() => navigate('/login')}
              className="btn-primary w-full"
            >
              {t('oauth.backToLogin')}
            </button>
            <button
              onClick={() => window.location.reload()}
              className="btn-secondary w-full"
            >
              {t('oauth.tryAgain')}
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
