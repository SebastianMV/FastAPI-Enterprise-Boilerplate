import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { emailVerificationService } from '@/services/api';
import { CheckCircle, XCircle, Loader2, Mail } from 'lucide-react';

/**
 * Email verification page.
 * Handles the email verification flow when user clicks the verification link.
 */
export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'no-token'>('loading');
  const [message, setMessage] = useState('');

  // Clean token from URL immediately to prevent leakage via browser history
  useEffect(() => {
    if (token) {
      window.history.replaceState({}, '', '/verify-email');
    }
  }, [token]);

  // Verify email mutation
  const verifyMutation = useMutation({
    mutationFn: (token: string) => emailVerificationService.verifyEmail(token),
    onSuccess: (response) => {
      setStatus('success');
      setMessage(t('auth.emailVerifiedSuccess'));
    },
    onError: () => {
      setStatus('error');
      setMessage(t('auth.verificationError'));
    },
  });

  useEffect(() => {
    if (!token) {
      setStatus('no-token');
      setMessage(t('auth.noTokenMessage'));
      return;
    }

    // Basic token format validation: must be alphanumeric/URL-safe, reasonable length
    if (!/^[A-Za-z0-9_-]{10,512}$/.test(token)) {
      setStatus('error');
      setMessage(t('auth.verificationError'));
      return;
    }

    verifyMutation.mutate(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
      <div className="max-w-md w-full">
        <div className="card p-8 text-center">
          {/* Loading state */}
          {status === 'loading' && (
            <>
              <div className="mx-auto w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mb-6">
                <Loader2 className="w-8 h-8 text-primary-600 dark:text-primary-400 animate-spin" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                {t('auth.verifyEmail')}
              </h1>
              <p className="text-slate-500 dark:text-slate-400">
                {t('auth.verifyEmailDescription')}
              </p>
            </>
          )}

          {/* Success state */}
          {status === 'success' && (
            <>
              <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-6">
                <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                {t('auth.emailVerified')}
              </h1>
              <p className="text-slate-500 dark:text-slate-400 mb-6">
                {message}
              </p>
              <button
                onClick={() => navigate('/dashboard', { replace: true })}
                className="btn-primary w-full"
              >
                {t('auth.goToDashboard')}
              </button>
            </>
          )}

          {/* Error state */}
          {status === 'error' && (
            <>
              <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-6">
                <XCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                {t('auth.verificationFailed')}
              </h1>
              <p className="text-slate-500 dark:text-slate-400 mb-6">
                {message}
              </p>
              <div className="space-y-3">
                <Link to="/settings" className="btn-primary w-full block">
                  {t('auth.resendVerification')}
                </Link>
                <Link to="/dashboard" className="btn-secondary w-full block">
                  {t('auth.goToDashboard')}
                </Link>
              </div>
            </>
          )}

          {/* No token state */}
          {status === 'no-token' && (
            <>
              <div className="mx-auto w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 rounded-full flex items-center justify-center mb-6">
                <Mail className="w-8 h-8 text-yellow-600 dark:text-yellow-400" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                {t('auth.noTokenProvided')}
              </h1>
              <p className="text-slate-500 dark:text-slate-400 mb-6">
                {message}
              </p>
              <Link to="/dashboard" className="btn-primary w-full block">
                {t('auth.goToDashboard')}
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
