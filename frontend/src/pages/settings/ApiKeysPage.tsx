import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Check,
  Loader2,
  AlertCircle,
  Clock,
  Shield,
  Activity,
  Calendar,
  X
} from 'lucide-react';
import { apiKeysService, type ApiKey, type NewlyCreatedKey } from '@/services/apiKeysService';
import { ConfirmModal, AlertModal } from '@/components/common/Modal';

interface CreateKeyFormData {
  name: string;
  scopes: string;
  expires_in_days: number | null;
}

/**
 * API Keys management page.
 * Allows users to create, view, and revoke their API keys.
 */
export default function ApiKeysPage() {
  const { t } = useTranslation();
  
  const AVAILABLE_SCOPES = useMemo(() => [
    { value: 'users:read', label: t('apiKeys.scopes.usersRead'), description: t('apiKeys.scopes.usersReadDesc') },
    { value: 'users:write', label: t('apiKeys.scopes.usersWrite'), description: t('apiKeys.scopes.usersWriteDesc') },
    { value: 'roles:read', label: t('apiKeys.scopes.rolesRead'), description: t('apiKeys.scopes.rolesReadDesc') },
    { value: 'roles:write', label: t('apiKeys.scopes.rolesWrite'), description: t('apiKeys.scopes.rolesWriteDesc') },
    { value: 'api-keys:read', label: t('apiKeys.scopes.apiKeysRead'), description: t('apiKeys.scopes.apiKeysReadDesc') },
    { value: 'api-keys:write', label: t('apiKeys.scopes.apiKeysWrite'), description: t('apiKeys.scopes.apiKeysWriteDesc') },
  ], [t]);
  
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<NewlyCreatedKey | null>(null);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);
  const [deletingKeyId, setDeletingKeyId] = useState<string | null>(null);
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [showRevokedKeys, setShowRevokedKeys] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showRevokeModal, setShowRevokeModal] = useState(false);
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKey | null>(null);
  const keyClearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clipboardClearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: 'success' | 'error';
  }>({ isOpen: false, title: '', message: '', variant: 'success' });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateKeyFormData>();

  const fetchApiKeys = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await apiKeysService.list(showRevokedKeys);
      setApiKeys(response.items);
    } catch {
      setErrorMessage(t('apiKeys.loadError'));
    } finally {
      setIsLoading(false);
    }
    // t is intentionally excluded: stable ref in production (i18next),
    // but unstable in tests causing infinite re-render loops.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showRevokedKeys]);

  // Cleanup timers and sensitive data on unmount
  useEffect(() => {
    return () => {
      if (keyClearTimerRef.current) {
        clearTimeout(keyClearTimerRef.current);
        keyClearTimerRef.current = null;
      }
      if (clipboardClearTimerRef.current) {
        clearTimeout(clipboardClearTimerRef.current);
        clipboardClearTimerRef.current = null;
      }
      // Clear key from state on unmount
      setNewlyCreatedKey(null);
    };
  }, []);

  // Fetch API keys on mount
  useEffect(() => {
    fetchApiKeys();
  }, [fetchApiKeys]);

  const onCreateSubmit = async (data: CreateKeyFormData) => {
    setIsCreating(true);
    setErrorMessage(null);

    try {
      const createdKey = await apiKeysService.create({
        name: data.name,
        scopes: selectedScopes,
        expires_in_days: data.expires_in_days || null,
      });

      setNewlyCreatedKey(createdKey);
      // Auto-clear the key from memory after 5 minutes for security
      if (keyClearTimerRef.current) clearTimeout(keyClearTimerRef.current);
      keyClearTimerRef.current = setTimeout(() => setNewlyCreatedKey(null), 5 * 60 * 1000);
      setShowCreateModal(false);
      reset();
      setSelectedScopes([]);
      await fetchApiKeys();
    } catch {
      setErrorMessage(t('apiKeys.createError'));
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    setDeletingKeyId(keyId);
    try {
      await apiKeysService.revoke(keyId);
      setShowRevokeModal(false);
      setKeyToRevoke(null);
      setAlertModal({
        isOpen: true,
        title: t('apiKeys.revokedSuccess'),
        message: t('apiKeys.revokedMessage'),
        variant: 'success',
      });
      await fetchApiKeys();
    } catch {
      setShowRevokeModal(false);
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('apiKeys.revokeError'),
        variant: 'error',
      });
    } finally {
      setDeletingKeyId(null);
    }
  };

  const handleRevokeClick = (key: ApiKey) => {
    setKeyToRevoke(key);
    setShowRevokeModal(true);
  };

  const copyToClipboard = async (text: string, keyId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKeyId(keyId);
      setTimeout(() => setCopiedKeyId(null), 2000);
      // Auto-clear clipboard after 60 seconds (defense-in-depth)
      if (clipboardClearTimerRef.current) clearTimeout(clipboardClearTimerRef.current);
      clipboardClearTimerRef.current = setTimeout(async () => {
        try {
          const current = await navigator.clipboard.readText();
          if (current === text) {
            await navigator.clipboard.writeText('');
          }
        } catch { /* clipboard read may be denied */ }
      }, 60_000);
    } catch {
      // Clipboard write failed — silently ignore
    }
  };

  const toggleScope = (scope: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scope)
        ? prev.filter((s) => s !== scope)
        : [...prev, scope]
    );
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return t('apiKeys.never');
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t('apiKeys.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {t('apiKeys.subtitle')}
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t('apiKeys.createKey')}
        </button>
      </div>

      {/* Messages */}
      {errorMessage && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
          <button onClick={() => setErrorMessage(null)} className="ml-auto">
            <X className="w-4 h-4 text-red-500" />
          </button>
        </div>
      )}

      {/* Newly Created Key Modal */}
      {newlyCreatedKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card p-6 max-w-lg w-full mx-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Key className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                {t('apiKeys.keyCreatedTitle')}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
                {t('apiKeys.keyCreatedWarning')}
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('apiKeys.yourApiKey')}
                </label>
                <div className="flex items-center space-x-2">
                  <code className="flex-1 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm font-mono break-all">
                    {newlyCreatedKey.key}
                  </code>
                  <button
                    onClick={() => copyToClipboard(newlyCreatedKey.key, 'new-key')}
                    className="p-3 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                  >
                    {copiedKeyId === 'new-key' ? (
                      <Check className="w-5 h-5 text-green-600" />
                    ) : (
                      <Copy className="w-5 h-5 text-slate-400" />
                    )}
                  </button>
                </div>
              </div>

              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                <p className="text-sm text-amber-800 dark:text-amber-300">
                  <strong>{t('common.warning')}:</strong> {t('apiKeys.warningOnce')}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">{t('apiKeys.name')}:</span>
                  <span className="ml-2 font-medium">{newlyCreatedKey.name}</span>
                </div>
                <div>
                  <span className="text-slate-500">{t('apiKeys.prefix')}:</span>
                  <span className="ml-2 font-mono">{newlyCreatedKey.prefix}</span>
                </div>
                <div>
                  <span className="text-slate-500">{t('apiKeys.expires')}:</span>
                  <span className="ml-2">{formatDate(newlyCreatedKey.expires_at)}</span>
                </div>
                <div>
                  <span className="text-slate-500">{t('apiKeys.scopes')}:</span>
                  <span className="ml-2">{newlyCreatedKey.scopes.length || t('apiKeys.scopes')}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                if (keyClearTimerRef.current) clearTimeout(keyClearTimerRef.current);
                setNewlyCreatedKey(null);
              }}
              className="btn-primary w-full mt-6"
            >
              {t('apiKeys.savedKey')}
            </button>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                {t('apiKeys.createKey')}
              </h2>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  reset();
                  setSelectedScopes([]);
                }}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit(onCreateSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('apiKeys.keyName')}
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder={t('apiKeys.keyNamePlaceholder')}
                  maxLength={100}
                  {...register('name', { required: t('validation.required') })}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('apiKeys.expirationDays')}
                </label>
                <input
                  type="number"
                  className="input"
                  placeholder={t('apiKeys.expirationPlaceholder')}
                  min={1}
                  max={365}
                  {...register('expires_in_days', { valueAsNumber: true })}
                />
                <p className="mt-1 text-xs text-slate-500">
                  {t('apiKeys.expirationHelp')}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  {t('apiKeys.permissions')}
                </label>
                <div className="space-y-2">
                  {AVAILABLE_SCOPES.map((scope) => (
                    <label
                      key={scope.value}
                      className="flex items-center p-3 bg-slate-50 dark:bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                      <input
                        type="checkbox"
                        checked={selectedScopes.includes(scope.value)}
                        onChange={() => toggleScope(scope.value)}
                        className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                      />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          {scope.label}
                        </p>
                        <p className="text-xs text-slate-500">{scope.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {t('apiKeys.permissionsHelp')}
                </p>
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    reset();
                    setSelectedScopes([]);
                  }}
                  className="btn-secondary flex-1"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="btn-primary flex-1"
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      {t('common.loading')}
                    </>
                  ) : (
                    <>
                      <Key className="w-4 h-4 mr-2" />
                      {t('apiKeys.createKey')}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center space-x-4">
        <label className="flex items-center space-x-2 text-sm text-slate-600 dark:text-slate-400">
          <input
            type="checkbox"
            checked={showRevokedKeys}
            onChange={(e) => setShowRevokedKeys(e.target.checked)}
            className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
          />
          <span>{t('apiKeys.showRevokedKeys')}</span>
        </label>
      </div>

      {/* API Keys List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      ) : apiKeys.length === 0 ? (
        <div className="card p-12 text-center">
          <Key className="w-12 h-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
            {t('apiKeys.noKeysTitle')}
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-6">
            {t('apiKeys.noKeysDescription')}
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            {t('apiKeys.createKey')}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {apiKeys.map((key) => (
            <div
              key={key.id}
              className={`card p-6 ${
                !key.is_active || isExpired(key.expires_at)
                  ? 'opacity-60'
                  : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-4">
                  <div className={`p-3 rounded-lg ${
                    key.is_active && !isExpired(key.expires_at)
                      ? 'bg-primary-100 dark:bg-primary-900/30'
                      : 'bg-slate-100 dark:bg-slate-800'
                  }`}>
                    <Key className={`w-6 h-6 ${
                      key.is_active && !isExpired(key.expires_at)
                        ? 'text-primary-600 dark:text-primary-400'
                        : 'text-slate-400'
                    }`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-white">
                      {key.name}
                    </h3>
                    <div className="flex items-center space-x-2 mt-1">
                      <code className="text-xs font-mono text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                        {key.prefix}...
                      </code>
                      {!key.is_active && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
                          {t('apiKeys.revoked')}
                        </span>
                      )}
                      {key.is_active && isExpired(key.expires_at) && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                          {t('apiKeys.expired')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {key.is_active && (
                  <button
                    onClick={() => handleRevokeClick(key)}
                    disabled={deletingKeyId === key.id}
                    className="btn-danger text-sm"
                  >
                    {deletingKeyId === key.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4 mr-1" />
                        {t('apiKeys.revoke')}
                      </>
                    )}
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">{t('apiKeys.created')}</p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {formatDate(key.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">{t('apiKeys.expires')}</p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {formatDate(key.expires_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">{t('apiKeys.lastUsed')}</p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {formatDate(key.last_used_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Shield className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">{t('apiKeys.usage')}</p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {key.usage_count} {t('apiKeys.requests')}
                    </p>
                  </div>
                </div>
              </div>

              {key.scopes.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {key.scopes.map((scope) => (
                    <span
                      key={scope}
                      className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                    >
                      {scope}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Help Section */}
      <div className="card p-6 bg-slate-50 dark:bg-slate-800/50">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center">
          <Key className="w-5 h-5 mr-2" />
          {t('apiKeys.usingApiKeys')}
        </h3>
        <div className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
          <p>
            {t('apiKeys.usingDescription')}
          </p>
          <div>
            <p className="font-medium mb-1">{t('apiKeys.usageExample')}</p>
            <code className="block p-3 bg-slate-100 dark:bg-slate-900 rounded-lg text-xs overflow-x-auto">
              {t('apiKeys.usageExampleCommand')}
            </code>
          </div>
          <p>
            <strong>{t('apiKeys.bestPractices')}</strong> {t('apiKeys.bestPracticesText')}
          </p>
        </div>
      </div>

      {/* Revoke Confirmation Modal */}
      <ConfirmModal
        isOpen={showRevokeModal}
        onClose={() => {
          setShowRevokeModal(false);
          setKeyToRevoke(null);
        }}
        onConfirm={() => keyToRevoke && handleRevokeKey(keyToRevoke.id)}
        title={t('apiKeys.revokeTitle')}
        message={t('apiKeys.revokeMessage', { name: keyToRevoke?.name })}
        confirmText={t('apiKeys.revokeConfirm')}
        cancelText={t('common.cancel')}
        variant="danger"
        isLoading={deletingKeyId !== null}
      />

      {/* Alert Modal */}
      <AlertModal
        isOpen={alertModal.isOpen}
        onClose={() => setAlertModal({ ...alertModal, isOpen: false })}
        title={alertModal.title}
        message={alertModal.message}
        variant={alertModal.variant}
      />
    </div>
  );
}
