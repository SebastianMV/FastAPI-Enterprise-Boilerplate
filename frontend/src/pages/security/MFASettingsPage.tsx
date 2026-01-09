import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { 
  Shield, 
  ShieldCheck, 
  ShieldOff,
  QrCode, 
  Copy, 
  Check,
  Loader2,
  AlertCircle,
  CheckCircle,
  Key,
  ArrowLeft,
  Eye,
  EyeOff
} from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '@/services/api';

interface MFAStatus {
  mfa_enabled: boolean;
  mfa_type: string | null;
}

interface MFASetupResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

interface VerifyFormData {
  code: string;
}

interface DisableFormData {
  code: string;
  password: string;
}

/**
 * MFA Settings Page component.
 * Allows users to enable, configure, and disable Two-Factor Authentication.
 */
export default function MFASettingsPage() {
  const [mfaStatus, setMfaStatus] = useState<MFAStatus | null>(null);
  const [setupData, setSetupData] = useState<MFASetupResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSetupLoading, setIsSetupLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isDisabling, setIsDisabling] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [showDisableForm, setShowDisableForm] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const {
    register: registerVerify,
    handleSubmit: handleVerifySubmit,
    formState: { errors: verifyErrors },
    reset: resetVerifyForm,
  } = useForm<VerifyFormData>();

  const {
    register: registerDisable,
    handleSubmit: handleDisableSubmit,
    formState: { errors: disableErrors },
    reset: resetDisableForm,
  } = useForm<DisableFormData>();

  // Fetch MFA status on mount
  useEffect(() => {
    fetchMFAStatus();
  }, []);

  const fetchMFAStatus = async () => {
    try {
      setIsLoading(true);
      const response = await api.get<MFAStatus>('/api/v1/mfa/status');
      setMfaStatus(response.data);
    } catch {
      setErrorMessage('Failed to fetch MFA status');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetupMFA = async () => {
    try {
      setIsSetupLoading(true);
      setErrorMessage(null);
      const response = await api.post<MFASetupResponse>('/api/v1/mfa/setup');
      setSetupData(response.data);
    } catch {
      setErrorMessage('Failed to setup MFA. Please try again.');
    } finally {
      setIsSetupLoading(false);
    }
  };

  const onVerifySubmit = async (data: VerifyFormData) => {
    try {
      setIsVerifying(true);
      setErrorMessage(null);
      
      await api.post('/api/v1/mfa/verify', { code: data.code });
      
      setSuccessMessage('MFA has been successfully enabled!');
      setSetupData(null);
      resetVerifyForm();
      await fetchMFAStatus();
    } catch {
      setErrorMessage('Invalid verification code. Please try again.');
    } finally {
      setIsVerifying(false);
    }
  };

  const onDisableSubmit = async (data: DisableFormData) => {
    try {
      setIsDisabling(true);
      setErrorMessage(null);
      
      await api.post('/api/v1/mfa/disable', { 
        code: data.code,
        password: data.password 
      });
      
      setSuccessMessage('MFA has been disabled.');
      setShowDisableForm(false);
      resetDisableForm();
      await fetchMFAStatus();
    } catch {
      setErrorMessage('Failed to disable MFA. Check your code and password.');
    } finally {
      setIsDisabling(false);
    }
  };

  const copyToClipboard = async (text: string, index?: number) => {
    try {
      await navigator.clipboard.writeText(text);
      if (index !== undefined) {
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
      } else {
        setCopiedSecret(true);
        setTimeout(() => setCopiedSecret(false), 2000);
      }
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const copyAllBackupCodes = async () => {
    if (!setupData?.backup_codes) return;
    const allCodes = setupData.backup_codes.join('\n');
    await copyToClipboard(allCodes);
    setCopiedIndex(-1);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link 
          to="/profile" 
          className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-slate-600 dark:text-slate-400" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Two-Factor Authentication
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Secure your account with TOTP-based authentication
          </p>
        </div>
      </div>

      {/* Messages */}
      {successMessage && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center space-x-3">
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
          <p className="text-sm text-green-700 dark:text-green-300">{successMessage}</p>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
        </div>
      )}

      {/* Current Status */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-full ${
              mfaStatus?.mfa_enabled 
                ? 'bg-green-100 dark:bg-green-900/30' 
                : 'bg-slate-100 dark:bg-slate-800'
            }`}>
              {mfaStatus?.mfa_enabled ? (
                <ShieldCheck className="w-6 h-6 text-green-600 dark:text-green-400" />
              ) : (
                <ShieldOff className="w-6 h-6 text-slate-400" />
              )}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                {mfaStatus?.mfa_enabled ? '2FA is Enabled' : '2FA is Disabled'}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {mfaStatus?.mfa_enabled 
                  ? `Using ${mfaStatus.mfa_type?.toUpperCase() || 'TOTP'} authentication` 
                  : 'Your account is not protected with two-factor authentication'}
              </p>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            mfaStatus?.mfa_enabled
              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
              : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
          }`}>
            {mfaStatus?.mfa_enabled ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      {/* Setup Flow - When MFA is disabled */}
      {!mfaStatus?.mfa_enabled && !setupData && (
        <div className="card p-6">
          <div className="text-center">
            <Shield className="w-12 h-12 text-primary-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              Enable Two-Factor Authentication
            </h3>
            <p className="text-slate-500 dark:text-slate-400 mb-6 max-w-md mx-auto">
              Add an extra layer of security by requiring a verification code from your 
              authenticator app when signing in.
            </p>
            <button
              onClick={handleSetupMFA}
              disabled={isSetupLoading}
              className="btn-primary"
            >
              {isSetupLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Setting up...
                </>
              ) : (
                <>
                  <QrCode className="w-4 h-4 mr-2" />
                  Begin Setup
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* QR Code & Setup Instructions */}
      {setupData && !mfaStatus?.mfa_enabled && (
        <div className="space-y-6">
          {/* Step 1: Scan QR Code */}
          <div className="card p-6">
            <div className="flex items-center space-x-2 mb-4">
              <span className="flex items-center justify-center w-6 h-6 bg-primary-600 text-white text-sm font-bold rounded-full">
                1
              </span>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Scan QR Code
              </h3>
            </div>
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              Scan this QR code with your authenticator app (Google Authenticator, Authy, 1Password, etc.)
            </p>
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="bg-white p-4 rounded-lg shadow-sm">
                <img 
                  src={`data:image/png;base64,${setupData.qr_code}`}
                  alt="MFA QR Code"
                  className="w-48 h-48"
                />
              </div>
              <div className="flex-1 space-y-4">
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Can't scan? Enter this code manually:
                </p>
                <div className="flex items-center space-x-2">
                  <code className="flex-1 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm font-mono break-all">
                    {setupData.secret}
                  </code>
                  <button
                    onClick={() => copyToClipboard(setupData.secret)}
                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                    title="Copy secret"
                  >
                    {copiedSecret ? (
                      <Check className="w-5 h-5 text-green-600" />
                    ) : (
                      <Copy className="w-5 h-5 text-slate-400" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Step 2: Save Backup Codes */}
          <div className="card p-6">
            <div className="flex items-center space-x-2 mb-4">
              <span className="flex items-center justify-center w-6 h-6 bg-primary-600 text-white text-sm font-bold rounded-full">
                2
              </span>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Save Backup Codes
              </h3>
            </div>
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              Store these backup codes in a safe place. You can use them to access your account if you lose your authenticator.
            </p>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setShowBackupCodes(!showBackupCodes)}
                  className="text-sm text-primary-600 hover:text-primary-700 flex items-center"
                >
                  {showBackupCodes ? (
                    <>
                      <EyeOff className="w-4 h-4 mr-1" />
                      Hide Codes
                    </>
                  ) : (
                    <>
                      <Eye className="w-4 h-4 mr-1" />
                      Show Codes
                    </>
                  )}
                </button>
                <button
                  onClick={copyAllBackupCodes}
                  className="text-sm text-primary-600 hover:text-primary-700 flex items-center"
                >
                  {copiedIndex === -1 ? (
                    <>
                      <Check className="w-4 h-4 mr-1" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-1" />
                      Copy All
                    </>
                  )}
                </button>
              </div>
              {showBackupCodes && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {setupData.backup_codes.map((code, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-2 bg-slate-100 dark:bg-slate-800 rounded-lg"
                    >
                      <code className="text-sm font-mono">{code}</code>
                      <button
                        onClick={() => copyToClipboard(code, index)}
                        className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                      >
                        {copiedIndex === index ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4 text-slate-400" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                <p className="text-sm text-amber-800 dark:text-amber-300">
                  <strong>Warning:</strong> These codes will only be shown once. Make sure to save them now!
                </p>
              </div>
            </div>
          </div>

          {/* Step 3: Verify */}
          <div className="card p-6">
            <div className="flex items-center space-x-2 mb-4">
              <span className="flex items-center justify-center w-6 h-6 bg-primary-600 text-white text-sm font-bold rounded-full">
                3
              </span>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Verify Setup
              </h3>
            </div>
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              Enter the 6-digit code from your authenticator app to complete setup.
            </p>
            <form onSubmit={handleVerifySubmit(onVerifySubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Verification Code
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="000000"
                  className="input max-w-xs text-center text-2xl tracking-widest font-mono"
                  {...registerVerify('code', { 
                    required: 'Code is required',
                    pattern: {
                      value: /^\d{6}$/,
                      message: 'Code must be 6 digits'
                    }
                  })}
                />
                {verifyErrors.code && (
                  <p className="mt-1 text-sm text-red-600">{verifyErrors.code.message}</p>
                )}
              </div>
              <div className="flex space-x-3">
                <button
                  type="submit"
                  disabled={isVerifying}
                  className="btn-primary"
                >
                  {isVerifying ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4 mr-2" />
                      Enable 2FA
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setSetupData(null)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MFA Enabled - Disable Option */}
      {mfaStatus?.mfa_enabled && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
            Disable Two-Factor Authentication
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-4">
            Disabling 2FA will make your account less secure. You'll need to verify your identity to proceed.
          </p>
          
          {!showDisableForm ? (
            <button
              onClick={() => setShowDisableForm(true)}
              className="btn-danger"
            >
              <ShieldOff className="w-4 h-4 mr-2" />
              Disable 2FA
            </button>
          ) : (
            <form onSubmit={handleDisableSubmit(onDisableSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Current 2FA Code
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="000000"
                  className="input max-w-xs text-center tracking-widest font-mono"
                  {...registerDisable('code', { 
                    required: 'Code is required',
                    pattern: {
                      value: /^\d{6}$/,
                      message: 'Code must be 6 digits'
                    }
                  })}
                />
                {disableErrors.code && (
                  <p className="mt-1 text-sm text-red-600">{disableErrors.code.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  className="input max-w-xs"
                  {...registerDisable('password', { required: 'Password is required' })}
                />
                {disableErrors.password && (
                  <p className="mt-1 text-sm text-red-600">{disableErrors.password.message}</p>
                )}
              </div>
              <div className="flex space-x-3">
                <button
                  type="submit"
                  disabled={isDisabling}
                  className="btn-danger"
                >
                  {isDisabling ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Disabling...
                    </>
                  ) : (
                    <>
                      <ShieldOff className="w-4 h-4 mr-2" />
                      Confirm Disable
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowDisableForm(false);
                    resetDisableForm();
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Help Section */}
      <div className="card p-6 bg-slate-50 dark:bg-slate-800/50">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center">
          <Key className="w-5 h-5 mr-2" />
          About Two-Factor Authentication
        </h3>
        <div className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
          <p>
            Two-factor authentication adds an extra layer of security to your account by 
            requiring both your password and a time-based code from your authenticator app.
          </p>
          <p>
            <strong>Recommended apps:</strong> Google Authenticator, Microsoft Authenticator, 
            Authy, 1Password, or any TOTP-compatible app.
          </p>
          <p>
            <strong>Lost your device?</strong> Use one of your backup codes to sign in, 
            then reconfigure 2FA with a new device.
          </p>
        </div>
      </div>
    </div>
  );
}
