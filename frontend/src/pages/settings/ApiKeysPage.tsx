import { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
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
import api from '@/services/api';
import { ConfirmModal, AlertModal } from '@/components/common/Modal';

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  usage_count: number;
  created_at: string;
}

interface CreateKeyFormData {
  name: string;
  scopes: string;
  expires_in_days: number | null;
}

interface NewlyCreatedKey {
  id: string;
  name: string;
  prefix: string;
  key: string;
  scopes: string[];
  expires_at: string | null;
  created_at: string;
}

const AVAILABLE_SCOPES = [
  { value: 'users:read', label: 'Read Users', description: 'View user information' },
  { value: 'users:write', label: 'Write Users', description: 'Create and update users' },
  { value: 'roles:read', label: 'Read Roles', description: 'View roles and permissions' },
  { value: 'roles:write', label: 'Write Roles', description: 'Manage roles' },
  { value: 'api-keys:read', label: 'Read API Keys', description: 'View API keys' },
  { value: 'api-keys:write', label: 'Write API Keys', description: 'Manage API keys' },
];

/**
 * API Keys management page.
 * Allows users to create, view, and revoke their API keys.
 */
export default function ApiKeysPage() {
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
      const response = await api.get(`/api/v1/api-keys?include_revoked=${showRevokedKeys}`);
      setApiKeys(response.data.items);
    } catch {
      setErrorMessage('Failed to load API keys');
    } finally {
      setIsLoading(false);
    }
  }, [showRevokedKeys]);

  // Fetch API keys on mount
  useEffect(() => {
    fetchApiKeys();
  }, [fetchApiKeys]);

  const onCreateSubmit = async (data: CreateKeyFormData) => {
    setIsCreating(true);
    setErrorMessage(null);

    try {
      const response = await api.post('/api/v1/api-keys', {
        name: data.name,
        scopes: selectedScopes,
        expires_in_days: data.expires_in_days || null,
      });

      setNewlyCreatedKey(response.data);
      setShowCreateModal(false);
      reset();
      setSelectedScopes([]);
      await fetchApiKeys();
    } catch {
      setErrorMessage('Failed to create API key');
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    setDeletingKeyId(keyId);
    try {
      await api.delete(`/api/v1/api-keys/${keyId}`);
      setShowRevokeModal(false);
      setKeyToRevoke(null);
      setAlertModal({
        isOpen: true,
        title: 'API Key Revoked',
        message: 'The API key has been revoked successfully and can no longer be used.',
        variant: 'success',
      });
      await fetchApiKeys();
    } catch {
      setShowRevokeModal(false);
      setAlertModal({
        isOpen: true,
        title: 'Error',
        message: 'Failed to revoke API key. Please try again.',
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
    } catch {
      console.error('Failed to copy');
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
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
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
            API Keys
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Manage your API keys for programmatic access
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary"
        >
          <Plus className="w-4 h-4 mr-2" />
          Create API Key
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card p-6 max-w-lg w-full mx-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Key className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                API Key Created!
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
                Copy your API key now. You won't be able to see it again!
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Your API Key
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
                  <strong>Warning:</strong> This key will only be shown once. Store it securely!
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Name:</span>
                  <span className="ml-2 font-medium">{newlyCreatedKey.name}</span>
                </div>
                <div>
                  <span className="text-slate-500">Prefix:</span>
                  <span className="ml-2 font-mono">{newlyCreatedKey.prefix}</span>
                </div>
                <div>
                  <span className="text-slate-500">Expires:</span>
                  <span className="ml-2">{formatDate(newlyCreatedKey.expires_at)}</span>
                </div>
                <div>
                  <span className="text-slate-500">Scopes:</span>
                  <span className="ml-2">{newlyCreatedKey.scopes.length || 'All'}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => setNewlyCreatedKey(null)}
              className="btn-primary w-full mt-6"
            >
              I've Saved My Key
            </button>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Create API Key
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
                  Key Name
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g., Production CI/CD"
                  {...register('name', { required: 'Name is required' })}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Expiration (days)
                </label>
                <input
                  type="number"
                  className="input"
                  placeholder="Leave empty for no expiration"
                  min={1}
                  max={365}
                  {...register('expires_in_days', { valueAsNumber: true })}
                />
                <p className="mt-1 text-xs text-slate-500">
                  Leave empty for a key that never expires
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Permissions (Scopes)
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
                  Leave all unchecked for full access
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
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="btn-primary flex-1"
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Key className="w-4 h-4 mr-2" />
                      Create Key
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
          <span>Show revoked keys</span>
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
            No API Keys
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-6">
            Create your first API key to get started with programmatic access.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create API Key
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
                          Revoked
                        </span>
                      )}
                      {key.is_active && isExpired(key.expires_at) && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                          Expired
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
                        Revoke
                      </>
                    )}
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">Created</p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {formatDate(key.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">Expires</p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {formatDate(key.expires_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">Last Used</p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {formatDate(key.last_used_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Shield className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">Usage</p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {key.usage_count} requests
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
          Using API Keys
        </h3>
        <div className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
          <p>
            API keys provide programmatic access to the API without requiring user authentication.
          </p>
          <div>
            <p className="font-medium mb-1">Usage example:</p>
            <code className="block p-3 bg-slate-100 dark:bg-slate-900 rounded-lg text-xs overflow-x-auto">
              curl -H "X-API-Key: your_api_key_here" https://api.example.com/v1/users
            </code>
          </div>
          <p>
            <strong>Best practices:</strong> Use separate keys for different applications,
            set appropriate expiration dates, and revoke keys that are no longer needed.
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
        title="Revoke API Key"
        message={`Are you sure you want to revoke the API key "${keyToRevoke?.name}"? This action cannot be undone and the key will immediately stop working.`}
        confirmText="Revoke Key"
        cancelText="Cancel"
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
