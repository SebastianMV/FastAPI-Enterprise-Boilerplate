import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
  Mail, 
  ArrowLeft, 
  Loader2, 
  CheckCircle,
  AlertCircle,
  Send
} from 'lucide-react';

interface ForgotPasswordFormData {
  email: string;
}

/**
 * Forgot Password page component.
 * Allows users to request a password reset email.
 */
export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>();

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await fetch('/auth/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: data.email }),
      });

      // Even if user doesn't exist, we show success for security
      // Backend should handle this gracefully
      if (response.ok || response.status === 404) {
        setIsSuccess(true);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || 'Failed to process request');
      }
    } catch {
      // For security, still show success even on errors
      // This prevents email enumeration attacks
      setIsSuccess(true);
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <div className="group relative rounded-2xl p-8 bg-white border border-slate-200 shadow-2xl transition-all duration-300 hover:-translate-y-1 hover:shadow-3xl overflow-hidden">
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 mb-2">
                {t('auth.resetLinkSent')}
              </h1>
              <p className="text-slate-500 mb-6">
                {t('auth.checkEmailReset')}
              </p>
              <div className="space-y-3">
                <p className="text-sm text-slate-500">
                  Didn't receive the email? Check your spam folder or try again.
                </p>
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <button
                    onClick={() => setIsSuccess(false)}
                    className="btn-secondary"
                  >
                    <Mail className="w-4 h-4 mr-2" />
                    Try Another Email
                  </button>
                  <Link to="/login" className="btn-primary">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    {t('auth.backToLogin')}
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="group relative rounded-2xl p-8 bg-white border border-slate-200 shadow-2xl transition-all duration-300 hover:-translate-y-1 hover:shadow-3xl overflow-hidden">
          
          {/* Logo & Header */}
          <div className="relative text-center mb-6">
            <div className="relative inline-flex items-center justify-center mb-6">
              <img src="/logo.png" alt="Boilerplate" className="relative w-24 h-24 drop-shadow-lg" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900">
              {t('auth.forgotPasswordTitle')}
            </h1>
            <p className="text-slate-500 mt-1">
              {t('auth.forgotPasswordDescription')}
            </p>
          </div>

          {/* Error message */}
          {errorMessage && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{errorMessage}</p>
            </div>
          )}

          {/* Form */}
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="space-y-5 transition-transform duration-200 group-hover:translate-y-0"
            noValidate
          >
            <div className="transition-colors duration-200">
              <label 
                htmlFor="email" 
                className="block text-sm font-medium text-slate-700 mb-1"
              >
                {t('auth.emailAddress')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder={t('auth.enterEmail')}
                  className="input pl-10 shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
                  {...register('email', {
                    required: t('validation.required'),
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: t('validation.emailInvalid'),
                    },
                  })}
                />
              </div>
              {errors.email && (
                <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
              )}
            </div>

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
                <>
                  <Send className="w-4 h-4 mr-2" />
                  {t('auth.sendResetLink')}
                </>
              )}
            </button>
          </form>

          {/* Back to Login link */}
          <div className="mt-6 text-center">
            <Link 
              to="/login" 
              className="text-sm text-primary-600 hover:text-primary-700 flex items-center justify-center"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              {t('auth.backToLogin')}
            </Link>
          </div>

          {/* Help text */}
          <p className="mt-4 text-center text-sm text-slate-500">
            Remember your password?{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
              {t('auth.signIn')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
