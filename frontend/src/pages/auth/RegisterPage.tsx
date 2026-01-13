import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { 
  AlertCircle, 
  Loader2, 
  Eye, 
  EyeOff,
  UserPlus,
  CheckCircle,
  Mail,
  Lock,
  User
} from 'lucide-react';
import api from '@/services/api';

interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
  first_name: string;
  last_name: string;
}

/**
 * Registration page component.
 * Allows new users to create an account.
 */
export default function RegisterPage() {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<RegisterFormData>();

  const password = watch('password');

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      await api.post('/auth/register', {
        email: data.email,
        password: data.password,
        first_name: data.first_name,
        last_name: data.last_name,
      });

      setIsSuccess(true);
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { data?: { detail?: { message?: string } | string } } };
        const detail = axiosError.response?.data?.detail;
        if (typeof detail === 'object' && detail?.message) {
          setErrorMessage(detail.message);
        } else if (typeof detail === 'string') {
          setErrorMessage(detail);
        } else {
          setErrorMessage('Registration failed. Please try again.');
        }
      } else {
        setErrorMessage('Registration failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Success state
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
                {t('auth.loginSuccess')}
              </h1>
              <p className="text-slate-500 mb-6">
                {t('auth.nowYouCanLogin')}
              </p>
              <Link to="/login" className="btn-primary w-full justify-center">
                {t('auth.signIn')}
              </Link>
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
          
          {/* Logo */}
          <div className="relative text-center mb-6">
            <div className="relative inline-flex items-center justify-center mb-6">
              <img src="/logo.png" alt="Boilerplate" className="relative w-24 h-24 drop-shadow-lg" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900">
              {t('auth.createAccount')}
            </h1>
            <p className="text-slate-500 mt-1">
              {t('auth.getStarted')}
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
            className="space-y-4 transition-transform duration-200 group-hover:translate-y-0"
            noValidate
          >
        {/* Name fields */}
        <div className="grid grid-cols-2 gap-4">
          <div className="transition-colors duration-200">
            <label
              htmlFor="first_name"
              className="block text-sm font-medium text-slate-700 mb-1"
            >
              {t('auth.firstName')}
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-5 w-5 text-slate-400" />
              </div>
              <input
                id="first_name"
                type="text"
                autoComplete="given-name"
                autoFocus
                className="input pl-10 shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
                placeholder="John"
                {...register('first_name', {
                  required: t('validation.required'),
                  minLength: { value: 1, message: t('validation.required') },
                })}
              />
            </div>
            {errors.first_name && (
              <p className="mt-1 text-sm text-red-600">{errors.first_name.message}</p>
            )}
          </div>

          <div className="transition-colors duration-200">
            <label
              htmlFor="last_name"
              className="block text-sm font-medium text-slate-700 mb-1"
            >
              {t('auth.lastName')}
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-5 w-5 text-slate-400" />
              </div>
              <input
                id="last_name"
                type="text"
                autoComplete="family-name"
                className="input pl-10 shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
                placeholder="Doe"
                {...register('last_name', {
                  required: t('validation.required'),
                  minLength: { value: 1, message: t('validation.required') },
                })}
              />
            </div>
            {errors.last_name && (
              <p className="mt-1 text-sm text-red-600">{errors.last_name.message}</p>
            )}
          </div>
        </div>

        {/* Email */}
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
              className="input pl-10 shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
              placeholder="you@example.com"
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

        {/* Password */}
        <div className="transition-colors duration-200">
          <label
            htmlFor="password"
            className="block text-sm font-medium text-slate-700 mb-1"
          >
            {t('auth.password')}
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Lock className="h-5 w-5 text-slate-400" />
            </div>
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              className="input pl-10 pr-10 shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
              placeholder="••••••••"
              {...register('password', {
                required: t('validation.required'),
                minLength: {
                  value: 8,
                  message: t('validation.passwordMin', { min: 8 }),
                },
                pattern: {
                  value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                  message: t('validation.passwordStrength'),
                },
              })}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
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
        <div className="transition-colors duration-200">
          <label
            htmlFor="confirmPassword"
            className="block text-sm font-medium text-slate-700 mb-1"
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
              className="input pl-10 pr-10 shadow-sm border border-slate-300 hover:border-primary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30"
              placeholder="••••••••"
              {...register('confirmPassword', {
                required: t('validation.required'),
                validate: (value) =>
                  value === password || t('profile.passwordsNoMatch'),
              })}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
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
        <div className="p-3 bg-slate-50 rounded-lg">
          <p className="text-xs font-medium text-slate-600 mb-2">
            Password requirements:
          </p>
          <ul className="text-xs text-slate-500 space-y-1">
            <li className={password?.length >= 8 ? 'text-green-600' : ''}>
              • At least 8 characters
            </li>
            <li className={password && /[A-Z]/.test(password) ? 'text-green-600' : ''}>
              • One uppercase letter
            </li>
            <li className={password && /[a-z]/.test(password) ? 'text-green-600' : ''}>
              • One lowercase letter
            </li>
            <li className={password && /\d/.test(password) ? 'text-green-600' : ''}>
              • One number
            </li>
          </ul>
        </div>

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
            <>
              <UserPlus className="w-4 h-4 mr-2" />
              {t('auth.createAccount')}
            </>
          )}
        </button>
      </form>

      {/* Sign in link */}
      <p className="mt-4 text-center text-sm text-slate-500">
        {t('auth.alreadyHaveAccount')}{' '}
        <Link
          to="/login"
          className="text-primary-600 hover:text-primary-700 font-medium"
        >
          {t('auth.signIn')}
        </Link>
      </p>
        </div>
      </div>
    </div>
  );
}
