import { AlertModal, ConfirmModal, Modal } from "@/components/common/Modal";
import { rolesService, usersService, type User } from "@/services/api";
import { maskEmail, sanitizeText } from "@/utils/security";
import { EMAIL_PATTERN, PASSWORD_PATTERN } from "@/utils/validation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  Edit,
  Loader2,
  Lock,
  Mail,
  Plus,
  RefreshCw,
  Search,
  Shield,
  Trash2,
  User as UserIcon,
  UserPlus,
  XCircle,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

interface CreateUserFormData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[]; // Role IDs
}

interface EditUserFormData {
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  roles: string[]; // Role IDs
}

/**
 * Users management page with full CRUD operations.
 */
export default function UsersPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: "success" | "error";
  }>({ isOpen: false, title: "", message: "", variant: "success" });
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const queryClient = useQueryClient();

  // Fetch users
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["users", page],
    queryFn: () =>
      usersService.list({ skip: (page - 1) * pageSize, limit: pageSize }),
  });

  // Fetch available roles for assignment
  const { data: rolesData } = useQuery({
    queryKey: ["roles"],
    queryFn: () => rolesService.list({ limit: 100 }),
  });
  const availableRoles = rolesData?.items || [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateUserFormData) => usersService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setShowCreateModal(false);
      resetCreateForm();
      setAlertModal({
        isOpen: true,
        title: t("users.userCreated"),
        message: t("users.createSuccess"),
        variant: "success",
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t("common.error"),
        message: t("users.createError"),
        variant: "error",
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<User> }) =>
      usersService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setShowEditModal(false);
      setSelectedUser(null);
      setAlertModal({
        isOpen: true,
        title: t("users.userUpdated"),
        message: t("users.updateSuccess"),
        variant: "success",
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t("common.error"),
        message: t("users.updateError"),
        variant: "error",
      });
    },
  });

  // Delete mutation (soft delete)
  const deleteMutation = useMutation({
    mutationFn: usersService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setShowDeleteModal(false);
      setSelectedUser(null);
      setAlertModal({
        isOpen: true,
        title: t("users.userDeleted"),
        message: t("users.deleteSuccess"),
        variant: "success",
      });
    },
    onError: () => {
      setAlertModal({
        isOpen: true,
        title: t("common.error"),
        message: t("users.deleteError"),
        variant: "error",
      });
    },
  });

  // Create form
  const {
    register: registerCreate,
    handleSubmit: handleCreateSubmit,
    reset: resetCreateForm,
    watch: watchCreate,
    setValue: setCreateValue,
    formState: { errors: createErrors },
  } = useForm<CreateUserFormData>({
    defaultValues: {
      is_active: true,
      is_superuser: false,
      roles: [],
    },
  });
  const selectedCreateRoles = watchCreate("roles") || [];

  // Edit form
  const {
    register: registerEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEditForm,
    watch: watchEdit,
    setValue: setEditValue,
    formState: { errors: editErrors },
  } = useForm<EditUserFormData>();
  const selectedEditRoles = watchEdit("roles") || [];

  const handleEditClick = useCallback(
    (user: User) => {
      setSelectedUser(user);
      resetEditForm({
        email: user.email,
        first_name: user.first_name,
        last_name: user.last_name,
        is_active: user.is_active,
        roles: user.roles || [],
      });
      setShowEditModal(true);
    },
    [resetEditForm],
  );

  const handleDeleteClick = useCallback((user: User) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
  }, []);

  const onCreateSubmit = useCallback(
    (data: CreateUserFormData) => {
      createMutation.mutate(data);
    },
    [createMutation],
  );

  const onEditSubmit = useCallback(
    (data: EditUserFormData) => {
      if (!selectedUser) return;
      updateMutation.mutate({ id: selectedUser.id, data });
    },
    [selectedUser, updateMutation],
  );

  const onDeleteConfirm = useCallback(() => {
    if (!selectedUser) return;
    deleteMutation.mutate(selectedUser.id);
  }, [selectedUser, deleteMutation]);

  const filteredUsers = useMemo(
    () =>
      (data?.items ?? []).filter(
        (user) =>
          user.email.toLowerCase().includes(search.toLowerCase()) ||
          (user.first_name ?? "")
            .toLowerCase()
            .includes(search.toLowerCase()) ||
          (user.last_name ?? "").toLowerCase().includes(search.toLowerCase()),
      ),
    [data?.items, search],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t("users.title")}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {t("users.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="btn-secondary"
            title={t("users.refreshUsers")}
            aria-label={t("users.refreshUsers")}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            {t("users.addUser")}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <input
          type="text"
          placeholder={t("users.searchPlaceholder")}
          className="input pl-10"
          value={search}
          maxLength={200}
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
            <p className="text-red-600 mb-4">{t("users.loadError")}</p>
            <button onClick={() => refetch()} className="btn-primary">
              <RefreshCw className="w-4 h-4 mr-2" />
              {t("common.retry")}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t("users.email")}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t("users.status")}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t("users.role")}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t("users.createdAt")}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {t("common.actions")}
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
                      {t("users.noUsersFound")}
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
                              {(user.first_name ?? "").charAt(0)}
                            </span>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-slate-900 dark:text-white">
                              {sanitizeText(user.first_name ?? "")}{" "}
                              {sanitizeText(user.last_name ?? "")}
                            </div>
                            <div className="text-sm text-slate-500">
                              {maskEmail(user.email)}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            user.is_active
                              ? "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400"
                              : "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400"
                          }`}
                        >
                          {user.is_active ? (
                            <>
                              <CheckCircle className="w-3 h-3 mr-1" />
                              {t("users.active")}
                            </>
                          ) : (
                            <>
                              <XCircle className="w-3 h-3 mr-1" />
                              {t("users.inactive")}
                            </>
                          )}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex flex-wrap gap-1">
                          {user.is_superuser && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400">
                              <Shield className="w-3 h-3 mr-1" />
                              {t("settings.administrator")}
                            </span>
                          )}
                          {user.roles && user.roles.length > 0
                            ? user.roles.map((roleId) => {
                                const role = availableRoles.find(
                                  (r) => r.id === roleId,
                                );
                                return role ? (
                                  <span
                                    key={roleId}
                                    className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400"
                                  >
                                    {sanitizeText(role.name)}
                                  </span>
                                ) : null;
                              })
                            : !user.is_superuser && (
                                <span className="text-slate-400 dark:text-slate-500">
                                  {t("settings.user")}
                                </span>
                              )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            className="p-2 text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                            title={t("common.edit")}
                            aria-label={t("common.edit")}
                            onClick={() => handleEditClick(user)}
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                            title={t("common.delete")}
                            aria-label={t("common.delete")}
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

      {/* Pagination */}
      {data &&
        (() => {
          const totalPages = Math.ceil((data.total || 0) / pageSize);
          return (
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t("users.showingCount", {
                  showing: filteredUsers.length,
                  total: data.total,
                })}
              </p>
              {totalPages > 1 && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(page - 1)}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800"
                  >
                    {t("common.previous")}
                  </button>
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={page === totalPages}
                    className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800"
                  >
                    {t("common.next")}
                  </button>
                </div>
              )}
            </div>
          );
        })()}

      {/* Create User Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          resetCreateForm();
        }}
        title={t("users.createUser")}
        size="lg"
      >
        <form
          onSubmit={handleCreateSubmit(onCreateSubmit)}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("users.firstName")}
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  {...registerCreate("first_name", {
                    required: t("validation.required"),
                  })}
                  className="input pl-10"
                  placeholder={t("common.placeholderFirstName")}
                  maxLength={100}
                />
              </div>
              {createErrors.first_name && (
                <p className="text-xs text-red-500 mt-1">
                  {createErrors.first_name.message}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("users.lastName")}
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  {...registerCreate("last_name", {
                    required: t("validation.required"),
                  })}
                  className="input pl-10"
                  placeholder={t("common.placeholderLastName")}
                  maxLength={100}
                />
              </div>
              {createErrors.last_name && (
                <p className="text-xs text-red-500 mt-1">
                  {createErrors.last_name.message}
                </p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("users.email")}
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                {...registerCreate("email", {
                  required: t("validation.required"),
                  pattern: {
                    value: EMAIL_PATTERN,
                    message: t("validation.emailInvalid"),
                  },
                })}
                type="email"
                className="input pl-10"
                placeholder={t("common.placeholderEmail")}
                maxLength={254}
              />
            </div>
            {createErrors.email && (
              <p className="text-xs text-red-500 mt-1">
                {createErrors.email.message}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("users.password")}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                {...registerCreate("password", {
                  required: t("validation.required"),
                  minLength: {
                    value: 8,
                    message: t("validation.passwordMin", { min: 8 }),
                  },
                  pattern: {
                    value: PASSWORD_PATTERN,
                    message: t("validation.passwordComplexity"),
                  },
                })}
                type="password"
                autoComplete="new-password"
                spellCheck={false}
                className="input pl-10"
                placeholder="••••••••"
                maxLength={128}
              />
            </div>
            {createErrors.password && (
              <p className="text-xs text-red-500 mt-1">
                {createErrors.password.message}
              </p>
            )}
          </div>

          <div className="flex items-center space-x-6">
            <label className="flex items-center">
              <input
                {...registerCreate("is_active")}
                type="checkbox"
                className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-slate-700 dark:text-slate-300">
                {t("users.active")}
              </span>
            </label>
            <label className="flex items-center">
              <input
                {...registerCreate("is_superuser")}
                type="checkbox"
                className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-slate-700 dark:text-slate-300">
                {t("settings.administrator")}
              </span>
            </label>
          </div>

          {/* Roles selector */}
          {availableRoles.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                <Shield className="inline w-4 h-4 mr-1" />
                {t("users.role")}
              </label>
              <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto p-2 border border-slate-200 dark:border-slate-700 rounded-lg">
                {availableRoles.map((role) => (
                  <label key={role.id} className="flex items-center text-sm">
                    <input
                      type="checkbox"
                      checked={selectedCreateRoles.includes(role.id)}
                      onChange={(e) => {
                        const newRoles = e.target.checked
                          ? [...selectedCreateRoles, role.id]
                          : selectedCreateRoles.filter((id) => id !== role.id);
                        setCreateValue("roles", newRoles);
                      }}
                      className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
                    />
                    <span className="ml-2 text-slate-700 dark:text-slate-300">
                      {sanitizeText(role.name)}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={() => {
                setShowCreateModal(false);
                resetCreateForm();
              }}
              className="btn-secondary"
            >
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="btn-primary"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t("common.loading")}
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4 mr-2" />
                  {t("users.createUser")}
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
        title={t("users.editUser")}
        size="lg"
      >
        <form onSubmit={handleEditSubmit(onEditSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("users.firstName")}
              </label>
              <input
                {...registerEdit("first_name", {
                  required: t("validation.required"),
                })}
                className="input"
                maxLength={100}
              />
              {editErrors.first_name && (
                <p className="text-xs text-red-500 mt-1">
                  {editErrors.first_name.message}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t("users.lastName")}
              </label>
              <input
                {...registerEdit("last_name", {
                  required: t("validation.required"),
                })}
                className="input"
                maxLength={100}
              />
              {editErrors.last_name && (
                <p className="text-xs text-red-500 mt-1">
                  {editErrors.last_name.message}
                </p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t("users.email")}
            </label>
            <input
              {...registerEdit("email", {
                required: t("validation.required"),
                pattern: {
                  value: EMAIL_PATTERN,
                  message: t("validation.emailInvalid"),
                },
              })}
              type="email"
              className="input"
              maxLength={254}
            />
            {editErrors.email && (
              <p className="text-xs text-red-500 mt-1">
                {editErrors.email.message}
              </p>
            )}
          </div>

          <div className="flex items-center">
            <label className="flex items-center">
              <input
                {...registerEdit("is_active")}
                type="checkbox"
                className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-slate-700 dark:text-slate-300">
                {t("users.active")}
              </span>
            </label>
          </div>

          {/* Roles selector */}
          {availableRoles.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                <Shield className="inline w-4 h-4 mr-1" />
                {t("users.role")}
              </label>
              <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto p-2 border border-slate-200 dark:border-slate-700 rounded-lg">
                {availableRoles.map((role) => (
                  <label key={role.id} className="flex items-center text-sm">
                    <input
                      type="checkbox"
                      checked={selectedEditRoles.includes(role.id)}
                      onChange={(e) => {
                        const newRoles = e.target.checked
                          ? [...selectedEditRoles, role.id]
                          : selectedEditRoles.filter((id) => id !== role.id);
                        setEditValue("roles", newRoles);
                      }}
                      className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
                    />
                    <span className="ml-2 text-slate-700 dark:text-slate-300">
                      {sanitizeText(role.name)}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={() => {
                setShowEditModal(false);
                setSelectedUser(null);
              }}
              className="btn-secondary"
            >
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="btn-primary"
            >
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t("common.loading")}
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  {t("common.save")}
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
        title={t("users.deleteUser")}
        message={t("users.deleteConfirm")}
        confirmText={t("common.delete")}
        cancelText={t("common.cancel")}
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
