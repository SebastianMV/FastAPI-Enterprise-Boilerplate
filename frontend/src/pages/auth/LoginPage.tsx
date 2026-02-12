import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { AlertCircle, Loader2, Shield } from 'lucide-react';
import SocialLoginButtons from '@/components/auth/SocialLoginButtons';

interface LoginFormData {
  email: string;
  password: string;
  mfa_code?: string;
}

/**
 * Login page component.
 */
export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [requiresMFA, setRequiresMFA] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<LoginFormData>();

  const onSubmit = async (data: LoginFormData) => {
    try {
      clearError();
      await login(data);
      navigate('/dashboard');
    } catch (err: unknown) {
      // Check if MFA is required
      if (err && typeof err === 'object' && 'response' in err) {
        const error = err as { response?: { data?: { detail?: { code?: string } } } };
        if (error?.response?.data?.detail?.code === 'MFA_REQUIRED') {
          setRequiresMFA(true);
          setError('root', {
            message: t('auth.mfa.enterCode'),
          });
        }
      }
      // Error is handled by the store
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="group relative rounded-2xl p-8 bg-white border border-slate-200 shadow-2xl transition-all duration-300 hover:-translate-y-1 hover:shadow-3xl overflow-hidden">
          
          {/* Logo */}
          <div className="relative text-center mb-6">
            <div className="relative inline-flex items-center justify-center mb-6">
              <img src="/logo.png" alt={t('common.brandLogoAlt')} className="relative w-24 h-24 drop-shadow-lg" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900">
              {t('auth.welcomeBack')}
            </h1>
            <p className="text-slate-500 mt-1">
              {t('auth.signInAccount')}
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{t(error)}</p>
            </div>
          )}

          {/* Form */}
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="space-y-5 transition-transform duration-200 group-hover:translate-y-0"
            noValidate
          >
            {/* Email */}
            <div className="transition-colors duration-200">
              <label
                htmlFor="email"
                className="block text-sm font-medium text-slate-700 mb-1"
              >
                {t('auth.emailAddress')}
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                autoFocus
                className="input shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
                placeholder={t('auth.enterEmail')}
                {...register('email', {
                  required: t('validation.required'),
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: t('validation.emailInvalid'),
                  },
                })}
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div className="transition-colors duration-200">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-slate-700 mb-1"
              >
                {t('auth.password')}
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  className="input pr-10 shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
                  placeholder="••••••••"
                  {...register('password', {
                    required: t('validation.required'),
                    minLength: {
                      value: 8,
                      message: t('validation.passwordMin', { min: 8 }),
                    },
                  })}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
              )}
              <div className="flex justify-end">
                <Link
                  to="/forgot-password"
                  className="text-sm text-primary-600 hover:text-primary-700"
                >
                  {t('auth.forgotPassword')}
                </Link>
              </div>
            </div>

            {/* MFA Code - shown when MFA is required */}
            {requiresMFA && (
              <div className="transition-colors duration-200">
                <label
                  htmlFor="mfa_code"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  <Shield className="w-4 h-4 inline mr-1" />
                  {t('auth.mfa.code')}
                </label>
                <input
                  id="mfa_code"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  autoFocus
                  className="input text-center text-2xl tracking-widest font-mono shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
                  placeholder="000000"
                  {...register('mfa_code', {
                    required: requiresMFA ? t('validation.required') : false,
                    pattern: {
                      value: /^\d{6}$/,
                      message: t('auth.mfa.codeMustBe6Digits'),
                    },
                  })}
                />
                {errors.mfa_code && (
                  <p className="mt-1 text-sm text-red-600">{errors.mfa_code.message}</p>
                )}
                <p className="mt-1 text-sm text-slate-500">
                  {t('auth.mfa.description')}
                </p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full shadow-lg shadow-primary-900/10 hover:shadow-primary-500/30 hover:-translate-y-[1px] transition-transform"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t('common.loading')}
                </>
              ) : (
                t('auth.signIn')
              )}
            </button>
          </form>

          {/* Register link */}
          <p className="mt-4 text-center text-sm text-slate-500">
            {t('auth.dontHaveAccount')}{' '}
            <Link
              to="/register"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              {t('auth.signUp')}
            </Link>
          </p>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-slate-500">{t('auth.orContinueWith')}</span>
            </div>
          </div>

          {/* Social Login Buttons */}
          <SocialLoginButtons
            mode="login"
            onError={(err) => {
              // Show error using the store
              useAuthStore.getState().setError(err);
            }}
          />
        </div>
      </div>
    </div>
  );
}
