import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { emailVerificationService } from '@/services/api';
import { AlertTriangle, Mail, X, Loader2, CheckCircle } from 'lucide-react';

/**
 * Banner that shows when user's email is not verified.
 * Includes a resend verification button.
 */
export default function EmailVerificationBanner() {
  const user = useAuthStore((state) => state.user);
  const [dismissed, setDismissed] = useState(false);
  const [sent, setSent] = useState(false);

  // Resend verification mutation
  const resendMutation = useMutation({
    mutationFn: emailVerificationService.sendVerification,
    onSuccess: () => {
      setSent(true);
    },
  });

  // Don't show if email is verified or dismissed
  if (!user || user.email_verified || dismissed) {
    return null;
  }

  return (
    <div className="bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              <span className="font-medium">Verify your email</span>
              {' — '}
              Please verify your email address to access all features.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {sent ? (
              <span className="flex items-center text-sm text-green-600 dark:text-green-400">
                <CheckCircle className="w-4 h-4 mr-1" />
                Verification email sent!
              </span>
            ) : (
              <button
                onClick={() => resendMutation.mutate()}
                disabled={resendMutation.isPending}
                className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-yellow-800 dark:text-yellow-200 bg-yellow-100 dark:bg-yellow-900/40 hover:bg-yellow-200 dark:hover:bg-yellow-900/60 rounded-md transition-colors disabled:opacity-50"
              >
                {resendMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                ) : (
                  <Mail className="w-4 h-4 mr-1" />
                )}
                Resend verification
              </button>
            )}

            <button
              onClick={() => setDismissed(true)}
              className="p-1 text-yellow-600 dark:text-yellow-400 hover:text-yellow-800 dark:hover:text-yellow-200"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
