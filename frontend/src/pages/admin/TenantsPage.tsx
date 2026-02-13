import { AlertModal, ConfirmModal, Modal } from '@/components/common/Modal';
import { tenantsService, type CreateTenantData, type Tenant, type UpdateTenantData } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { maskEmail, sanitizeCssColor, sanitizeText } from '@/utils/security';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    AlertTriangle,
    Building2,
    Calendar,
    CheckCircle,
    Crown,
    Edit,
    Globe,
    Loader2,
    Mail,
    Plus,
    RefreshCw,
    Search,
    Settings,
    ShieldCheck,
    Trash2,
    Users,
    XCircle,
} from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';

// Plan badges
const planColors: Record<string, string> = {
  free: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  starter: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  professional: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  enterprise: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
};

interface CreateTenantFormData {
  name: string;
  slug: string;
  email?: string;
  phone?: string;
  domain?: string;
  timezone: string;
  locale: string;
  plan: string;
}

interface EditTenantFormData {
  name: string;
  slug: string;
  email?: string;
  phone?: string;
  domain?: string;
  timezone: string;
  locale: string;
  plan: string;
}

/**
 * Tenant (Organization) management page for superusers.
 */
export default function TenantsPage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: 'success' | 'error';
  }>({ isOpen: false, title: '', message: '', variant: 'success' });

  const queryClient = useQueryClient();

  // Fetch tenants - hooks must be called before any conditional returns
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tenants', statusFilter],
    queryFn: () => tenantsService.list({
      limit: 100,
      is_active: statusFilter === 'all' ? undefined : statusFilter === 'active',
    }),
    enabled: !!user?.is_superuser,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateTenantData) => tenantsService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setShowCreateModal(false);
      resetCreateForm();
      setAlertModal({
        isOpen: true,
        title: t('tenants.tenantCreated'),
        message: t('tenants.createSuccess'),
        variant: 'success',
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('tenants.createError'),
        variant: 'error',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTenantData }) =>
      tenantsService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setShowEditModal(false);
      setSelectedTenant(null);
      setAlertModal({
        isOpen: true,
        title: t('tenants.tenantUpdated'),
        message: t('tenants.updateSuccess'),
        variant: 'success',
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('tenants.updateError'),
        variant: 'error',
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: tenantsService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setShowDeleteModal(false);
      setSelectedTenant(null);
      setAlertModal({
        isOpen: true,
        title: t('tenants.tenantDeleted'),
        message: t('tenants.deleteSuccess'),
        variant: 'success',
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('tenants.deleteError'),
        variant: 'error',
      });
    },
  });

  // Activate mutation
  const activateMutation = useMutation({
    mutationFn: (id: string) => tenantsService.activate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setAlertModal({
        isOpen: true,
        title: t('tenants.tenantActivated'),
        message: t('tenants.activateSuccess'),
        variant: 'success',
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('tenants.activateError'),
        variant: 'error',
      });
    },
  });

  // Deactivate mutation
  const deactivateMutation = useMutation({
    mutationFn: (id: string) => tenantsService.deactivate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setAlertModal({
        isOpen: true,
        title: t('tenants.tenantDeactivated'),
        message: t('tenants.deactivateSuccess'),
        variant: 'success',
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('tenants.deactivateError'),
        variant: 'error',
      });
    },
  });

  // Create form
  const {
    register: registerCreate,
    handleSubmit: handleCreateSubmit,
    reset: resetCreateForm,
    formState: { errors: createErrors },
  } = useForm<CreateTenantFormData>({
    defaultValues: {
      timezone: 'UTC',
      locale: 'en',
      plan: 'free',
    },
  });

  // Edit form
  const {
    register: registerEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEditForm,
  } = useForm<EditTenantFormData>();

  // Filter tenants by search
  const filteredTenants = data?.items?.filter((tenant) =>
    tenant.name.toLowerCase().includes(search.toLowerCase()) ||
    tenant.slug.toLowerCase().includes(search.toLowerCase()) ||
    tenant.email?.toLowerCase().includes(search.toLowerCase())
  ) || [];

  // Helper to clean empty strings from form data
  const cleanFormData = <T extends object>(data: T): Partial<T> => {
    const cleaned: Partial<T> = {};
    for (const [key, value] of Object.entries(data)) {
      if (value !== '' && value !== undefined && value !== null) {
        (cleaned as Record<string, unknown>)[key] = value;
      }
    }
    return cleaned;
  };

  // Handle create
  const onCreateSubmit = (formData: CreateTenantFormData) => {
    const cleaned = cleanFormData(formData);
    // Ensure required fields are present
    if (cleaned.name && cleaned.slug) {
      createMutation.mutate(cleaned as CreateTenantFormData);
    }
  };

  // Handle edit
  const onEditSubmit = (formData: EditTenantFormData) => {
    if (selectedTenant) {
      updateMutation.mutate({
        id: selectedTenant.id,
        data: cleanFormData(formData) as UpdateTenantData,
      });
    }
  };

  // Handle delete
  const handleDelete = () => {
    if (selectedTenant) {
      deleteMutation.mutate(selectedTenant.id);
    }
  };

  // Open edit modal
  const openEditModal = (tenant: Tenant) => {
    setSelectedTenant(tenant);
    resetEditForm({
      name: tenant.name,
      slug: tenant.slug,
      email: tenant.email || '',
      phone: tenant.phone || '',
      domain: tenant.domain || '',
      timezone: tenant.timezone,
      locale: tenant.locale,
      plan: tenant.plan,
    });
    setShowEditModal(true);
  };

  // Toggle tenant status
  const toggleTenantStatus = (tenant: Tenant) => {
    if (tenant.is_active) {
      deactivateMutation.mutate(tenant.id);
    } else {
      activateMutation.mutate(tenant.id);
    }
  };

  // Check if user is superuser (after all hooks)
  if (!user?.is_superuser) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">{t('tenants.accessDenied')}</h2>
          <p className="text-gray-500 dark:text-gray-400">
            {t('tenants.accessDeniedMessage')}
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-500 mb-4">{t('tenants.loadError')}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('tenants.retry')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Building2 className="h-7 w-7" />
          {t('tenants.title')}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          {t('tenants.subtitle')}
        </p>
      </div>

      {/* Actions bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          {/* Search */}
          <div className="relative flex-1 sm:w-72">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder={t('tenants.searchPlaceholder')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              maxLength={200}
              autoComplete="off"
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as 'all' | 'active' | 'inactive')}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="all">{t('tenants.allStatus')}</option>
            <option value="active">{t('tenants.active')}</option>
            <option value="inactive">{t('tenants.inactive')}</option>
          </select>
        </div>

        {/* Create button */}
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          <Plus className="h-4 w-4 mr-2" />
          {t('tenants.createTenant')}
        </button>
      </div>

      {/* Tenants grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredTenants.map((tenant) => (
            <div
              key={tenant.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 hover:shadow-lg transition-shadow"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${tenant.is_active ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-gray-100 dark:bg-gray-700'}`}>
                    <Building2 className={`h-5 w-5 ${tenant.is_active ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      {sanitizeText(tenant.name)}
                      {tenant.is_verified && (
                        <ShieldCheck className="h-4 w-4 text-green-500" />
                      )}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">@{sanitizeText(tenant.slug)}</p>
                  </div>
                </div>

                {/* Status badge */}
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                  tenant.is_active
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                }`}>
                  {tenant.is_active ? (
                    <><CheckCircle className="h-3 w-3 mr-1" /> {t('tenants.active')}</>
                  ) : (
                    <><XCircle className="h-3 w-3 mr-1" /> {t('tenants.inactive')}</>
                  )}
                </span>
              </div>

              {/* Plan badge */}
              <div className="mb-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${planColors[tenant.plan] || planColors.free}`}>
                  <Crown className="h-3 w-3 mr-1" />
                  {t(`tenants.plans.${tenant.plan}`)}
                </span>
              </div>

              {/* Details */}
              <div className="space-y-2 text-sm">
                {tenant.email && (
                  <div className="flex items-center text-gray-600 dark:text-gray-300">
                    <Mail className="h-4 w-4 mr-2 text-gray-400" />
                    {maskEmail(tenant.email)}
                  </div>
                )}
                {tenant.domain && (
                  <div className="flex items-center text-gray-600 dark:text-gray-300">
                    <Globe className="h-4 w-4 mr-2 text-gray-400" />
                    {sanitizeText(tenant.domain)}
                  </div>
                )}
                <div className="flex items-center text-gray-500 dark:text-gray-400">
                  <Calendar className="h-4 w-4 mr-2" />
                  {t('tenants.created')} {new Date(tenant.created_at).toLocaleDateString()}
                </div>
              </div>

              {/* Settings summary */}
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span className="flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    {t('tenants.maxUsers', { count: tenant.settings.max_users })}
                  </span>
                  <span>
                    {tenant.settings.enable_2fa && t('tenants.feature2fa')}
                    {tenant.settings.enable_api_keys && ` • ${t('tenants.featureApiKeys')}`}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-between">
                <div className="flex gap-2">
                  <button
                    onClick={() => openEditModal(tenant)}
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                    title={t('tenants.editTenant')}
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      setSelectedTenant(tenant);
                      setShowSettingsModal(true);
                    }}
                    className="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded transition-colors"
                    title={t('tenants.viewSettings')}
                  >
                    <Settings className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      setSelectedTenant(tenant);
                      setShowDeleteModal(true);
                    }}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                    title={t('tenants.deleteTenant')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <button
                  onClick={() => toggleTenantStatus(tenant)}
                  disabled={activateMutation.isPending || deactivateMutation.isPending}
                  className={`text-xs px-2 py-1 rounded disabled:opacity-50 ${
                    tenant.is_active
                      ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                      : 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                  }`}
                >
                  {tenant.is_active ? t('tenants.deactivate') : t('tenants.activate')}
                </button>
              </div>
            </div>
          ))}

          {filteredTenants.length === 0 && !isLoading && (
            <div className="col-span-full flex flex-col items-center justify-center py-12 text-gray-500">
              <Building2 className="h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg font-medium">{t('tenants.noTenantsFound')}</p>
              <p className="text-sm">
                {search ? t('tenants.tryDifferentSearch') : t('tenants.createFirstTenant')}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          resetCreateForm();
        }}
        title={t('tenants.createTenant')}
      >
        <form onSubmit={handleCreateSubmit(onCreateSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.name')} *
              </label>
              <input
                type="text"
                {...registerCreate('name', { required: t('tenants.nameRequired') })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                placeholder={t('tenants.namePlaceholder')}
                maxLength={200}
              />
              {createErrors.name && (
                <p className="mt-1 text-sm text-red-500">{createErrors.name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.slug')} *
              </label>
              <input
                type="text"
                {...registerCreate('slug', {
                  required: t('tenants.slugRequired'),
                  pattern: {
                    value: /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
                    message: t('tenants.slugPattern'),
                  },
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                placeholder={t('tenants.slugPlaceholder')}
                maxLength={100}
              />
              {createErrors.slug && (
                <p className="mt-1 text-sm text-red-500">{createErrors.slug.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.plan')}
              </label>
              <select
                {...registerCreate('plan')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="free">{t('tenants.plans.free')}</option>
                <option value="starter">{t('tenants.plans.starter')}</option>
                <option value="professional">{t('tenants.plans.professional')}</option>
                <option value="enterprise">{t('tenants.plans.enterprise')}</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.email')}
              </label>
              <input
                type="email"
                {...registerCreate('email')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                placeholder={t('tenants.emailPlaceholder')}
                maxLength={254}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.domain')}
              </label>
              <input
                type="text"
                {...registerCreate('domain')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                placeholder={t('tenants.domainPlaceholder')}
                maxLength={253}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.timezone')}
              </label>
              <input
                type="text"
                {...registerCreate('timezone')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                placeholder={t('tenants.timezonePlaceholder')}
                maxLength={50}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.locale')}
              </label>
              <select
                {...registerCreate('locale')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="en">{t('tenants.localeEnglish')}</option>
                <option value="es">{t('tenants.localeSpanish')}</option>
                <option value="pt">{t('tenants.localePortuguese')}</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => {
                setShowCreateModal(false);
                resetCreateForm();
              }}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {t('tenants.createTenant')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedTenant(null);
        }}
        title={t('tenants.editTenant')}
      >
        <form onSubmit={handleEditSubmit(onEditSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.name')} *
              </label>
              <input
                type="text"
                {...registerEdit('name', { required: t('tenants.nameRequired') })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                maxLength={200}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.slug')}
              </label>
              <input
                type="text"
                {...registerEdit('slug', {
                  pattern: {
                    value: /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
                    message: t('tenants.slugPattern'),
                  },
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                maxLength={100}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.plan')}
              </label>
              <select
                {...registerEdit('plan')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="free">{t('tenants.plans.free')}</option>
                <option value="starter">{t('tenants.plans.starter')}</option>
                <option value="professional">{t('tenants.plans.professional')}</option>
                <option value="enterprise">{t('tenants.plans.enterprise')}</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.email')}
              </label>
              <input
                type="email"
                {...registerEdit('email')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                maxLength={254}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('tenants.domain')}
              </label>
              <input
                type="text"
                {...registerEdit('domain')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                maxLength={253}
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => {
                setShowEditModal(false);
                setSelectedTenant(null);
              }}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {updateMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {t('tenants.saveChanges')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Settings Modal */}
      <Modal
        isOpen={showSettingsModal}
        onClose={() => {
          setShowSettingsModal(false);
          setSelectedTenant(null);
        }}
        title={t('tenants.tenantSettings')}
      >
        {selectedTenant && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.2faRequired')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {selectedTenant.settings.enable_2fa ? t('tenants.settings.yes') : t('tenants.settings.no')}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.apiKeysEnabled')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {selectedTenant.settings.enable_api_keys ? t('tenants.settings.yes') : t('tenants.settings.no')}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.webhooksEnabled')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {selectedTenant.settings.enable_webhooks ? t('tenants.settings.yes') : t('tenants.settings.no')}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.maxUsers')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {selectedTenant.settings.max_users}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.maxApiKeysPerUser')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {selectedTenant.settings.max_api_keys_per_user}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.maxStorageMb')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {selectedTenant.settings.max_storage_mb}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.passwordMinLength')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {selectedTenant.settings.password_min_length}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.sessionTimeout')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {t('tenants.settings.sessionTimeoutMinutes', { minutes: selectedTenant.settings.session_timeout_minutes })}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.emailVerification')}</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {selectedTenant.settings.require_email_verification ? t('tenants.settings.required') : t('tenants.settings.optional')}
                </p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('tenants.settings.primaryColor')}</span>
                <p className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
                  <span
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: sanitizeCssColor(selectedTenant.settings.primary_color) }}
                  />
                  {sanitizeCssColor(selectedTenant.settings.primary_color)}
                </p>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setSelectedTenant(null);
        }}
        onConfirm={handleDelete}
        title={t('tenants.deleteTenant')}
        message={t('tenants.deleteConfirm', { name: selectedTenant?.name || '' })}
        confirmText={t('common.delete')}
        variant="danger"
        isLoading={deleteMutation.isPending}
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
