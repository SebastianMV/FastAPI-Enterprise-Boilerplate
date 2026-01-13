import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { usersService, type User } from '@/services/api';
import { Modal, ConfirmModal, AlertModal } from '@/components/common/Modal';
import {
  Plus,
  Search,
  Edit,
  Trash2,
  Loader2,
  UserPlus,
  Mail,
  Lock,
  User as UserIcon,
  CheckCircle,
  XCircle,
  RefreshCw,
} from 'lucide-react';

interface CreateUserFormData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

interface EditUserFormData {
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
}

/**
 * Users management page with full CRUD operations.
 */
export default function UsersPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
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

  // Fetch users
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersService.list({ limit: 100 }),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateUserFormData) => usersService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowCreateModal(false);
      resetCreateForm();
      setAlertModal({
        isOpen: true,
        title: t('users.userCreated'),
        message: t('users.createSuccess'),
        variant: 'success',
      });
    },
    onError: (error: Error) => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: error.message || t('users.createError'),
        variant: 'error',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<User> }) =>
      usersService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowEditModal(false);
      setSelectedUser(null);
      setAlertModal({
        isOpen: true,
        title: t('users.userUpdated'),
        message: t('users.updateSuccess'),
        variant: 'success',
      });
    },
    onError: (error: Error) => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: error.message || t('users.updateError'),
        variant: 'error',
      });
    },
  });

  // Delete mutation (soft delete)
  const deleteMutation = useMutation({
    mutationFn: usersService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowDeleteModal(false);
      setSelectedUser(null);
      setAlertModal({
        isOpen: true,
        title: t('users.userDeleted'),
        message: t('users.deleteSuccess'),
        variant: 'success',
      });
    },
    onError: (error: Error) => {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: error.message || t('users.deleteError'),
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
  } = useForm<CreateUserFormData>({
    defaultValues: {
      is_active: true,
      is_superuser: false,
    },
  });

  // Edit form
  const {
    register: registerEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEditForm,
    formState: { errors: editErrors },
  } = useForm<EditUserFormData>();

  const handleEditClick = (user: User) => {
    setSelectedUser(user);
    resetEditForm({
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      is_active: user.is_active,
    });
    setShowEditModal(true);
  };

  const handleDeleteClick = (user: User) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
  };

  const onCreateSubmit = (data: CreateUserFormData) => {
    createMutation.mutate(data);
  };

  const onEditSubmit = (data: EditUserFormData) => {
    if (!selectedUser) return;
    updateMutation.mutate({ id: selectedUser.id, data });
  };

  const onDeleteConfirm = () => {
    if (!selectedUser) return;
    deleteMutation.mutate(selectedUser.id);
  };

  const users = data?.items || [];
  const filteredUsers = users.filter(
    (user) =>
      user.email.toLowerCase().includes(search.toLowerCase()) ||
      user.first_name.toLowerCase().includes(search.toLowerCase()) ||
      user.last_name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t('users.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Manage user accounts and permissions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="btn-secondary"
            title={t('users.refreshUsers')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            {t('users.addUser')}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <input
          type="text"
          placeholder={t('users.searchPlaceholder')}
          className="input pl-10"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Users table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-600 mb-4">{t('users.loadingUsers')}</p>
            <button onClick={() => refetch()} className="btn-primary">
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t('users.email')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t('users.status')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t('users.role')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t('users.createdAt')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t('common.actions')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-6 py-12 text-center text-slate-500"
                    >
                      {t('users.noUsersFound')}
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((user) => (
                    <tr
                      key={user.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/50"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
                            <span className="text-white font-medium">
                              {user.first_name.charAt(0)}
                            </span>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-slate-900 dark:text-white">
                              {user.first_name} {user.last_name}
                            </div>
                            <div className="text-sm text-slate-500">
                              {user.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            user.is_active
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                              : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                          }`}
                        >
                          {user.is_active ? (
                            <>
                              <CheckCircle className="w-3 h-3 mr-1" />
                              {t('users.active')}
                            </>
                          ) : (
                            <>
                              <XCircle className="w-3 h-3 mr-1" />
                              {t('users.inactive')}
                            </>
                          )}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                        {user.is_superuser ? t('settings.administrator') : t('settings.user')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            className="p-2 text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                            title={t('common.edit')}
                            onClick={() => handleEditClick(user)}
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                            title={t('common.delete')}
                            onClick={() => handleDeleteClick(user)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination info */}
      {data && (
        <div className="text-sm text-slate-500 dark:text-slate-400">
          Showing {filteredUsers.length} of {data.total} users
        </div>
      )}

      {/* Create User Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          resetCreateForm();
        }}
        title={t('users.createUser')}
        size="lg"
      >
        <form onSubmit={handleCreateSubmit(onCreateSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('users.firstName')}
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  {...registerCreate('first_name', { required: t('validation.required') })}
                  className="input pl-10"
                  placeholder="John"
                />
              </div>
              {createErrors.first_name && (
                <p className="text-xs text-red-500 mt-1">{createErrors.first_name.message}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('users.lastName')}
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  {...registerCreate('last_name', { required: t('validation.required') })}
                  className="input pl-10"
                  placeholder="Doe"
                />
              </div>
              {createErrors.last_name && (
                <p className="text-xs text-red-500 mt-1">{createErrors.last_name.message}</p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('users.email')}
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                {...registerCreate('email', {
                  required: t('validation.required'),
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: t('validation.emailInvalid'),
                  },
                })}
                type="email"
                className="input pl-10"
                placeholder="john.doe@example.com"
              />
            </div>
            {createErrors.email && (
              <p className="text-xs text-red-500 mt-1">{createErrors.email.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('users.password')}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                {...registerCreate('password', {
                  required: t('validation.required'),
                  minLength: {
                    value: 8,
                    message: t('validation.passwordMin', { min: 8 }),
                  },
                })}
                type="password"
                className="input pl-10"
                placeholder="••••••••"
              />
            </div>
            {createErrors.password && (
              <p className="text-xs text-red-500 mt-1">{createErrors.password.message}</p>
            )}
          </div>

          <div className="flex items-center space-x-6">
            <label className="flex items-center">
              <input
                {...registerCreate('is_active')}
                type="checkbox"
                className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-slate-700 dark:text-slate-300">{t('users.active')}</span>
            </label>
            <label className="flex items-center">
              <input
                {...registerCreate('is_superuser')}
                type="checkbox"
                className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-slate-700 dark:text-slate-300">{t('settings.administrator')}</span>
            </label>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={() => {
                setShowCreateModal(false);
                resetCreateForm();
              }}
              className="btn-secondary"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="btn-primary"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t('common.loading')}
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4 mr-2" />
                  {t('users.createUser')}
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit User Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedUser(null);
        }}
        title={t('users.editUser')}
        size="lg"
      >
        <form onSubmit={handleEditSubmit(onEditSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('users.firstName')}
              </label>
              <input
                {...registerEdit('first_name', { required: t('validation.required') })}
                className="input"
              />
              {editErrors.first_name && (
                <p className="text-xs text-red-500 mt-1">{editErrors.first_name.message}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('users.lastName')}
              </label>
              <input
                {...registerEdit('last_name', { required: t('validation.required') })}
                className="input"
              />
              {editErrors.last_name && (
                <p className="text-xs text-red-500 mt-1">{editErrors.last_name.message}</p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('users.email')}
            </label>
            <input
              {...registerEdit('email', {
                required: t('validation.required'),
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: t('validation.emailInvalid'),
                },
              })}
              type="email"
              className="input"
            />
            {editErrors.email && (
              <p className="text-xs text-red-500 mt-1">{editErrors.email.message}</p>
            )}
          </div>

          <div className="flex items-center">
            <label className="flex items-center">
              <input
                {...registerEdit('is_active')}
                type="checkbox"
                className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-slate-700 dark:text-slate-300">{t('users.active')}</span>
            </label>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={() => {
                setShowEditModal(false);
                setSelectedUser(null);
              }}
              className="btn-secondary"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="btn-primary"
            >
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t('common.loading')}
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  {t('common.save')}
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setSelectedUser(null);
        }}
        onConfirm={onDeleteConfirm}
        title={t('users.deleteUser')}
        message={t('users.deleteConfirm')}
        confirmText={t('common.delete')}
        cancelText={t('common.cancel')}
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
