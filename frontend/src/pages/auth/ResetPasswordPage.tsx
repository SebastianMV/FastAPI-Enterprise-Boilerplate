import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '@/services/api';
import { PASSWORD_PATTERN } from '@/utils/validation';
import { 
  Lock, 
  ArrowLeft, 
  Loader2, 
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff,
  ShieldCheck
} from 'lucide-react';

interface ResetPasswordFormData {
  password: string;
  confirmPassword: string;
}

/**
 * Reset Password page component.
 * Allows users to set a new password using a reset token.
 */
export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const [searchParams] = useSearchParams();
  
  const [isLoading, setIsLoading] = useState(false);
  const [isValidating, setIsValidating] = useState(true);
  const [isTokenValid, setIsTokenValid] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Get token from URL params or query string
  const resetToken = token || searchParams.get('token');

  // Clean the token from the URL immediately (prevent leakage via browser history)
  useEffect(() => {
    if (resetToken) {
      window.history.replaceState({}, '', '/reset-password');
    }
  }, [resetToken]);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<ResetPasswordFormData>();

  const password = watch('password');

  // Validate token on mount
  useEffect(() => {
    const controller = new AbortController();

    const validateToken = async () => {
      // Validate token format before sending to backend (defense-in-depth)
      if (!resetToken || !/^[A-Za-z0-9_-]{10,512}$/.test(resetToken)) {
        setIsTokenValid(false);
        setIsValidating(false);
        return;
      }

      try {
        await api.get('/auth/verify-reset-token', {
          params: { token: resetToken },
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setIsTokenValid(true);
        }
      } catch {
        // Token invalid or endpoint unavailable — fail-closed
        if (!controller.signal.aborted) {
          setIsTokenValid(false);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsValidating(false);
        }
      }
    };

    validateToken();

    return () => controller.abort();
  }, [resetToken]);

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!resetToken || isLoading) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await api.post('/auth/reset-password', {
        token: resetToken,
        new_password: data.password,
      });

      setIsSuccess(true);
    } catch {
      setErrorMessage(t('auth.resetFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state
  if (isValidating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600 mx-auto mb-4" />
          <p className="text-slate-500 dark:text-slate-400">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  // Invalid or missing token
  if (!resetToken || !isTokenValid) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
        <div className="max-w-md w-full">
          <div className="card p-8 text-center">
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
              {t('auth.invalidResetLink')}
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mb-6">
              {t('auth.resetLinkExpired')}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link to="/forgot-password" className="btn-primary">
                {t('auth.requestNewLink')}
              </Link>
              <Link to="/login" className="btn-secondary">
                <ArrowLeft className="w-4 h-4 mr-2" />
                {t('auth.backToLogin')}
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
        <div className="max-w-md w-full">
          <div className="card p-8 text-center">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
              {t('auth.passwordResetSuccess')}
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mb-6">
              {t('auth.nowYouCanLogin')}
            </p>
            <Link to="/login" className="btn-primary w-full justify-center">
              <ShieldCheck className="w-4 h-4 mr-2" />
              {t('auth.signIn')}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Reset form
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
      <div className="max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <Lock className="w-8 h-8 text-primary-600 dark:text-primary-400" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t('auth.resetPasswordTitle')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-2">
            {t('auth.resetPasswordDescription')}
          </p>
        </div>

        {/* Form */}
        <div className="card p-8">
          {errorMessage && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* New Password */}
            <div>
              <label 
                htmlFor="password" 
                className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
              >
                {t('profile.newPassword')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder={t('auth.enterPassword')}
                  spellCheck={false}
                  className="input pl-10 pr-10"
                  maxLength={128}
                  {...register('password', {
                    required: t('validation.required'),
                    minLength: {
                      value: 8,
                      message: t('validation.passwordMin', { min: 8 }),
                    },
                    pattern: {
                      value: PASSWORD_PATTERN,
                      message: t('validation.passwordStrength'),
                    },
                  })}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-slate-400 hover:text-slate-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-slate-400 hover:text-slate-600" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label 
                htmlFor="confirmPassword" 
                className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
              >
                {t('profile.confirmPassword')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder={t('auth.enterPassword')}
                  spellCheck={false}
                  className="input pl-10 pr-10"
                  maxLength={128}
                  {...register('confirmPassword', {
                    required: t('validation.required'),
                    validate: value => 
                      value === password || t('profile.passwordsNoMatch'),
                  })}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? t('auth.hidePassword') : t('auth.showPassword')}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-5 w-5 text-slate-400 hover:text-slate-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-slate-400 hover:text-slate-600" />
                  )}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-red-600">{errors.confirmPassword.message}</p>
              )}
            </div>

            {/* Password requirements */}
            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
                {t('auth.passwordRequirements')}
              </p>
              <ul className="text-xs text-slate-500 dark:text-slate-500 space-y-1">
                <li className={password?.length >= 8 ? 'text-green-600' : ''}>
                  • {t('auth.passwordReqMinChars')}
                </li>
                <li className={password && /[A-Z]/.test(password) ? 'text-green-600' : ''}>
                  • {t('auth.passwordReqUppercase')}
                </li>
                <li className={password && /[a-z]/.test(password) ? 'text-green-600' : ''}>
                  • {t('auth.passwordReqLowercase')}
                </li>
                <li className={password && /\d/.test(password) ? 'text-green-600' : ''}>
                  • {t('auth.passwordReqNumber')}
                </li>
                <li className={password && /[!@#$%^&*(),.?":{}|<>]/.test(password) ? 'text-green-600' : ''}>
                  • {t('auth.passwordReqSpecial')}
                </li>
              </ul>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full justify-center"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t('common.loading')}
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4 mr-2" />
                  {t('profile.updatePassword')}
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link 
              to="/login" 
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 flex items-center justify-center"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              {t('auth.backToLogin')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
