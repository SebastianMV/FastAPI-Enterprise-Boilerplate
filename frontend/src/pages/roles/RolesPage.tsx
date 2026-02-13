import { AlertModal, ConfirmModal, Modal } from '@/components/common/Modal';
import { rolesService, type Role } from '@/services/api';
import { sanitizeText } from '@/utils/security';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    Edit,
    Loader2,
    Lock,
    Plus,
    RefreshCw,
    Search,
    Shield,
    ShieldCheck,
    Trash2,
    Users,
} from 'lucide-react';
import { useState } from 'react';
import { Control, Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';

// Available permissions - matches backend Permission class
const AVAILABLE_PERMISSIONS = [
  { resource: 'users', actions: ['create', 'read', 'update', 'delete'] },
  { resource: 'roles', actions: ['create', 'read', 'update', 'delete'] },
  { resource: 'posts', actions: ['create', 'read', 'update', 'delete'] },
  { resource: 'comments', actions: ['create', 'read', 'update', 'delete'] },
  { resource: 'documents', actions: ['create', 'read', 'update', 'delete'] },
  { resource: 'settings', actions: ['read', 'update'] },
  { resource: 'audit_logs', actions: ['read'] },
  { resource: 'notifications', actions: ['create', 'read', 'update', 'delete'] },
  { resource: 'api_keys', actions: ['create', 'read', 'delete'] },
];

interface RoleFormData {
  name: string;
  description: string;
  permissions: string[];
}

type CreateRoleFormData = RoleFormData;
type EditRoleFormData = RoleFormData;

/**
 * Roles management page with CRUD operations.
 * Allows administrators to create, edit, and delete roles with custom permissions.
 */
export default function RolesPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: 'success' | 'error';
  }>({ isOpen: false, title: '', message: '', variant: 'success' });

  const queryClient = useQueryClient();

  // Fetch roles
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rolesService.list({ limit: 100 }),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateRoleFormData) => rolesService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setShowCreateModal(false);
      resetCreateForm();
      setAlertModal({
        isOpen: true,
        title: t('roles.roleCreated'),
        message: t('roles.createSuccess'),
        variant: 'success',
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('roles.createError'),
        variant: 'error',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Role> }) =>
      rolesService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setShowEditModal(false);
      setSelectedRole(null);
      setAlertModal({
        isOpen: true,
        title: t('roles.roleUpdated'),
        message: t('roles.updateSuccess'),
        variant: 'success',
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('roles.updateError'),
        variant: 'error',
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: rolesService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setShowDeleteModal(false);
      setSelectedRole(null);
      setAlertModal({
        isOpen: true,
        title: t('roles.roleDeleted'),
        message: t('roles.deleteSuccess'),
        variant: 'success',
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: t('roles.deleteError'),
        variant: 'error',
      });
    },
  });

  // Create form
  const {
    register: registerCreate,
    handleSubmit: handleCreateSubmit,
    reset: resetCreateForm,
    control: controlCreate,
    formState: { errors: createErrors },
  } = useForm<CreateRoleFormData>({
    defaultValues: {
      name: '',
      description: '',
      permissions: [],
    },
  });

  // Edit form
  const {
    register: registerEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEditForm,
    control: controlEdit,
    formState: { errors: editErrors },
  } = useForm<EditRoleFormData>();

  // Filter roles by search
  const filteredRoles = data?.items?.filter((role) =>
    role.name.toLowerCase().includes(search.toLowerCase()) ||
    role.description.toLowerCase().includes(search.toLowerCase())
  ) || [];

  // Handle create
  const onCreateSubmit = (formData: CreateRoleFormData) => {
    createMutation.mutate(formData);
  };

  // Handle edit
  const onEditSubmit = (formData: EditRoleFormData) => {
    if (selectedRole) {
      updateMutation.mutate({
        id: selectedRole.id,
        data: formData,
      });
    }
  };

  // Handle delete
  const handleDelete = () => {
    if (selectedRole) {
      deleteMutation.mutate(selectedRole.id);
    }
  };

  // Open edit modal
  const openEditModal = (role: Role) => {
    setSelectedRole(role);
    resetEditForm({
      name: role.name,
      description: role.description,
      permissions: role.permissions,
    });
    setShowEditModal(true);
  };

  // Open delete modal
  const openDeleteModal = (role: Role) => {
    setSelectedRole(role);
    setShowDeleteModal(true);
  };

  // Permission Checkbox Component
  const PermissionCheckboxGroup = ({
    control,
    name,
    disabled = false,
  }: {
    control: Control<RoleFormData>;
    name: 'permissions';
    disabled?: boolean;
  }) => (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
          {AVAILABLE_PERMISSIONS.map(({ resource, actions }) => (
            <div key={resource} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
              <div className="font-medium text-gray-900 dark:text-white capitalize mb-2">
                {t(`roles.resources.${resource}`)}
              </div>
              <div className="flex flex-wrap gap-2">
                {actions.map((action) => {
                  const permission = `${resource}:${action}`;
                  const isChecked = field.value?.includes(permission);
                  return (
                    <label
                      key={permission}
                      className={`inline-flex items-center px-3 py-1.5 rounded-md border cursor-pointer transition-colors ${
                        isChecked
                          ? 'bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900/30 dark:border-blue-500 dark:text-blue-300'
                          : 'bg-gray-50 border-gray-300 text-gray-600 hover:border-gray-400 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-300'
                      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <input
                        type="checkbox"
                        disabled={disabled}
                        checked={isChecked}
                        onChange={(e) => {
                          const newValue = e.target.checked
                            ? [...(field.value || []), permission]
                            : (field.value || []).filter((p: string) => p !== permission);
                          field.onChange(newValue);
                        }}
                        className="sr-only"
                      />
                      <span className="capitalize text-sm">{t(`roles.actions.${action}`)}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    />
  );

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-500 mb-4">{t('roles.loadError')}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('common.retry')}
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
          <Shield className="h-7 w-7" />
          {t('roles.title')}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          {t('roles.subtitle')}
        </p>
      </div>

      {/* Actions bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder={t('roles.searchPlaceholder')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            maxLength={200}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Create button */}
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          <Plus className="h-4 w-4 mr-2" />
          {t('roles.createRole')}
        </button>
      </div>

      {/* Roles grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredRoles.map((role) => (
            <div
              key={role.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 hover:shadow-lg transition-shadow"
            >
              {/* Role header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    role.is_system
                      ? 'bg-purple-100 dark:bg-purple-900/30'
                      : 'bg-blue-100 dark:bg-blue-900/30'
                  }`}>
                    {role.is_system ? (
                      <Lock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    ) : (
                      <ShieldCheck className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {sanitizeText(role.name)}
                    </h3>
                    {role.is_system && (
                      <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                        {t('roles.systemRole')}
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                {!role.is_system && (
                  <div className="flex gap-1">
                    <button
                      onClick={() => openEditModal(role)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                      title={t('roles.editRole')}
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => openDeleteModal(role)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                      title={t('roles.deleteRole')}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>

              {/* Description */}
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 line-clamp-2">
                {role.description ? sanitizeText(role.description) : t('roles.noDescription')}
              </p>

              {/* Permissions count */}
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                <Users className="h-4 w-4" />
                <span>{t('roles.permissionCount', { count: role.permissions.length })}</span>
              </div>

              {/* Permission tags */}
              {role.permissions.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {role.permissions.slice(0, 4).map((perm) => (
                    <span
                      key={perm}
                      className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                    >
                      {sanitizeText(perm)}
                    </span>
                  ))}
                  {role.permissions.length > 4 && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200">
                      +{role.permissions.length - 4} {t('roles.more')}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}

          {filteredRoles.length === 0 && !isLoading && (
            <div className="col-span-full flex flex-col items-center justify-center py-12 text-gray-500">
              <Shield className="h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg font-medium">{t('roles.noRolesFound')}</p>
              <p className="text-sm">
                {search ? t('roles.tryDifferentSearch') : t('roles.createFirstRole')}
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
        title={t('roles.createRole')}
      >
        <form onSubmit={handleCreateSubmit(onCreateSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('roles.roleName')} *
            </label>
            <input
              type="text"
              {...registerCreate('name', {
                required: t('validation.required'),
                minLength: { value: 2, message: t('validation.minLength', { min: 2 }) },
                maxLength: { value: 100, message: t('validation.maxLength', { max: 100 }) },
              })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder={t('roles.namePlaceholder')}
            />
            {createErrors.name && (
              <p className="mt-1 text-sm text-red-500">{createErrors.name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('roles.description')}
            </label>
            <textarea
              {...registerCreate('description')}
              rows={2}
              maxLength={500}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder={t('roles.descriptionPlaceholder')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('roles.permissions')}
            </label>
            <PermissionCheckboxGroup control={controlCreate} name="permissions" />
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
              {t('roles.createRole')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedRole(null);
        }}
        title={t('roles.editRole')}
      >
        <form onSubmit={handleEditSubmit(onEditSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('roles.roleName')} *
            </label>
            <input
              type="text"
              {...registerEdit('name', {
                required: t('validation.required'),
                minLength: { value: 2, message: t('validation.minLength', { min: 2 }) },
                maxLength: { value: 100, message: t('validation.maxLength', { max: 100 }) },
              })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {editErrors.name && (
              <p className="mt-1 text-sm text-red-500">{editErrors.name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('roles.description')}
            </label>
            <textarea
              {...registerEdit('description')}
              rows={2}
              maxLength={500}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('roles.permissions')}
            </label>
            <PermissionCheckboxGroup control={controlEdit} name="permissions" />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => {
                setShowEditModal(false);
                setSelectedRole(null);
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
              {t('common.save')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setSelectedRole(null);
        }}
        onConfirm={handleDelete}
        title={t('roles.deleteRole')}
        message={t('roles.deleteConfirm', { name: selectedRole?.name })}
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
