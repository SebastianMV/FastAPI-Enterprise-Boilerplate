import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
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
  is_enabled: boolean;
  enabled_at: string | null;
  backup_codes_remaining: number;
  last_used_at: string | null;
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
  const { t } = useTranslation();
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
      const response = await api.get<MFAStatus>('/mfa/status');
      setMfaStatus(response.data);
    } catch {
      setErrorMessage(t('mfa.fetchError'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetupMFA = async () => {
    try {
      setIsSetupLoading(true);
      setErrorMessage(null);
      const response = await api.post<MFASetupResponse>('/mfa/setup');
      setSetupData(response.data);
    } catch {
      setErrorMessage(t('mfa.setupError'));
    } finally {
      setIsSetupLoading(false);
    }
  };

  const onVerifySubmit = async (data: VerifyFormData) => {
    try {
      setIsVerifying(true);
      setErrorMessage(null);
      
      await api.post('/mfa/verify', { code: data.code });
      
      setSuccessMessage(t('mfa.enableSuccess'));
      setSetupData(null);
      resetVerifyForm();
      await fetchMFAStatus();
    } catch {
      setErrorMessage(t('mfa.enableError'));
    } finally {
      setIsVerifying(false);
    }
  };

  const onDisableSubmit = async (data: DisableFormData) => {
    try {
      setIsDisabling(true);
      setErrorMessage(null);
      
      await api.post('/mfa/disable', { 
        code: data.code,
        password: data.password 
      });
      
      setSuccessMessage(t('mfa.disableSuccess'));
      setShowDisableForm(false);
      resetDisableForm();
      await fetchMFAStatus();
    } catch {
      setErrorMessage(t('mfa.disableError'));
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
            {t('mfa.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {t('mfa.subtitle')}
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
              mfaStatus?.is_enabled 
                ? 'bg-green-100 dark:bg-green-900/30' 
                : 'bg-slate-100 dark:bg-slate-800'
            }`}>
              {mfaStatus?.is_enabled ? (
                <ShieldCheck className="w-6 h-6 text-green-600 dark:text-green-400" />
              ) : (
                <ShieldOff className="w-6 h-6 text-slate-400" />
              )}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                {mfaStatus?.is_enabled ? t('mfa.enabled') : t('mfa.disabled')}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {mfaStatus?.is_enabled 
                  ? t('mfa.usingTotp') 
                  : t('mfa.notProtected')}
              </p>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            mfaStatus?.is_enabled
              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
              : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
          }`}>
            {mfaStatus?.is_enabled ? t('mfa.active') : t('mfa.inactive')}
          </span>
        </div>
      </div>

      {/* Setup Flow - When MFA is disabled */}
      {!mfaStatus?.is_enabled && !setupData && (
        <div className="card p-6">
          <div className="text-center">
            <Shield className="w-12 h-12 text-primary-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              {t('mfa.enableTitle')}
            </h3>
            <p className="text-slate-500 dark:text-slate-400 mb-6 max-w-md mx-auto">
              {t('mfa.enableDescription')}
            </p>
            <button
              onClick={handleSetupMFA}
              disabled={isSetupLoading}
              className="btn-primary"
            >
              {isSetupLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t('mfa.settingUp')}
                </>
              ) : (
                <>
                  <QrCode className="w-4 h-4 mr-2" />
                  {t('mfa.beginSetup')}
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* QR Code & Setup Instructions */}
      {setupData && !mfaStatus?.is_enabled && (
        <div className="space-y-6">
          {/* Step 1: Scan QR Code */}
          <div className="card p-6">
            <div className="flex items-center space-x-2 mb-4">
              <span className="flex items-center justify-center w-6 h-6 bg-primary-600 text-white text-sm font-bold rounded-full">
                1
              </span>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                {t('mfa.step1Title')}
              </h3>
            </div>
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              {t('mfa.step1Description')}
            </p>
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="bg-white p-4 rounded-lg shadow-sm">
                <img 
                  src={setupData.qr_code}
                  alt="MFA QR Code"
                  className="w-48 h-48"
                />
              </div>
              <div className="flex-1 space-y-4">
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {t('mfa.cantScan')}
                </p>
                <div className="flex items-center space-x-2">
                  <code className="flex-1 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm font-mono break-all text-slate-900 dark:text-white">
                    {setupData.secret}
                  </code>
                  <button
                    onClick={() => copyToClipboard(setupData.secret)}
                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                    title={t('mfa.copySecret')}
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
                {t('mfa.step2Title')}
              </h3>
            </div>
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              {t('mfa.step2Description')}
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
                      {t('mfa.hideCodes')}
                    </>
                  ) : (
                    <>
                      <Eye className="w-4 h-4 mr-1" />
                      {t('mfa.showCodes')}
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
                      {t('mfa.copied')}
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-1" />
                      {t('mfa.copyAll')}
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
                  <strong>{t('common.warning')}:</strong> {t('mfa.backupWarning')}
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
                {t('mfa.step3Title')}
              </h3>
            </div>
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              {t('mfa.step3Description')}
            </p>
            <form onSubmit={handleVerifySubmit(onVerifySubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('mfa.verificationCode')}
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="000000"
                  className="input max-w-xs text-center text-2xl tracking-widest font-mono"
                  {...registerVerify('code', { 
                    required: t('mfa.codeRequired'),
                    pattern: {
                      value: /^\d{6}$/,
                      message: t('mfa.codeInvalid')
                    }
                  })}
                />
                {verifyErrors.code && (
                  <p className="mt-1 text-sm text-red-600">{verifyErrors.code.message}</p>
                )}
              </div>
              {errorMessage && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
                  <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
                </div>
              )}
              <div className="flex space-x-3">
                <button
                  type="submit"
                  disabled={isVerifying}
                  className="btn-primary"
                >
                  {isVerifying ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      {t('mfa.verifying')}
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4 mr-2" />
                      {t('mfa.enable2fa')}
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setSetupData(null)}
                  className="btn-secondary"
                >
                  {t('common.cancel')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MFA Enabled - Disable Option */}
      {mfaStatus?.is_enabled && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
            {t('mfa.disableTitle')}
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-4">
            {t('mfa.disableDescription')}
          </p>
          
          {!showDisableForm ? (
            <button
              onClick={() => setShowDisableForm(true)}
              className="btn-danger"
            >
              <ShieldOff className="w-4 h-4 mr-2" />
              {t('mfa.disable2fa')}
            </button>
          ) : (
            <form onSubmit={handleDisableSubmit(onDisableSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('mfa.current2faCode')}
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="000000"
                  className="input max-w-xs text-center tracking-widest font-mono"
                  {...registerDisable('code', { 
                    required: t('mfa.codeRequired'),
                    pattern: {
                      value: /^\d{6}$/,
                      message: t('mfa.codeInvalid')
                    }
                  })}
                />
                {disableErrors.code && (
                  <p className="mt-1 text-sm text-red-600">{disableErrors.code.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('mfa.password')}
                </label>
                <input
                  type="password"
                  className="input max-w-xs"
                  {...registerDisable('password', { required: t('mfa.passwordRequired') })}
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
                      {t('mfa.disabling')}
                    </>
                  ) : (
                    <>
                      <ShieldOff className="w-4 h-4 mr-2" />
                      {t('mfa.confirmDisable')}
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
                  {t('common.cancel')}
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
          {t('mfa.aboutTitle')}
        </h3>
        <div className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
          <p>
            {t('mfa.aboutDescription')}
          </p>
          <p>
            <strong>{t('auth.mfa.backupCodes')}:</strong> {t('mfa.recommendedApps')}
          </p>
          <p>
            <strong>{t('mfa.lostDevice').split(':')[0]}?</strong> {t('mfa.lostDevice').split(':').slice(1).join(':') || t('mfa.lostDevice')}
          </p>
        </div>
      </div>
    </div>
  );
}
