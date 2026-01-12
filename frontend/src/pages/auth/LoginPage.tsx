import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
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
            message: 'Please enter your 6-digit authentication code',
          });
        }
      }
      // Error is handled by the store
    }
  };

  return (
    <div className="card p-8">
      {/* Logo */}
      <div className="text-center mb-3">
        <div className="inline-flex items-center justify-center w-48 h-48 mb-4">
          <img src="/logo.png" alt="Boilerplate" className="w-48 h-48" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Welcome back
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Sign in to your account
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        {/* Email */}
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
          >
            Email address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            autoFocus
            className="input"
            placeholder="you@example.com"
            {...register('email', {
              required: 'El correo es obligatorio',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Ingresa un correo válido (ej: nombre@dominio.com)',
              },
            })}
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>

        {/* Password */}
        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
          >
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              className="input pr-10"
              placeholder="••••••••"
              {...register('password', {
                required: 'La contraseña es obligatoria',
                minLength: {
                  value: 8,
                  message: 'La contraseña debe tener al menos 8 caracteres',
                },
              })}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          {errors.password && (
            <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
          )}
          <div className="flex justify-end">
            <a 
              href="/forgot-password" 
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400"
            >
              Forgot password?
            </a>
          </div>
        </div>

        {/* MFA Code - shown when MFA is required */}
        {requiresMFA && (
          <div>
            <label
              htmlFor="mfa_code"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              <Shield className="w-4 h-4 inline mr-1" />
              Authentication Code
            </label>
            <input
              id="mfa_code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              autoFocus
              className="input text-center text-2xl tracking-widest font-mono"
              placeholder="000000"
              {...register('mfa_code', {
                required: requiresMFA ? 'MFA code is required' : false,
                pattern: {
                  value: /^\d{6}$/,
                  message: 'Code must be 6 digits',
                },
              })}
            />
            {errors.mfa_code && (
              <p className="mt-1 text-sm text-red-600">{errors.mfa_code.message}</p>
            )}
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Signing in...
            </>
          ) : (
            'Sign in'
          )}
        </button>
      </form>

      {/* Demo credentials */}
      <div className="mt-6 p-4 bg-slate-100 dark:bg-slate-700/50 rounded-lg">
        <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
          Demo credentials:
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Email: test@example.com<br />
          Password: Test123!
        </p>
      </div>

      {/* Register link */}
      <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
        Don't have an account?{' '}
        <a
          href="/register"
          className="text-primary-600 hover:text-primary-700 font-medium"
        >
          Create one
        </a>
      </p>

      {/* Divider */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-200 dark:border-slate-700" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white dark:bg-slate-800 text-slate-500">
            Or continue with
          </span>
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
  );
}
