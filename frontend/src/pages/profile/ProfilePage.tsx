import { useState, useRef, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { usersService } from '@/services/api';
import ConnectedAccounts from '@/components/profile/ConnectedAccounts';
import { ConfirmModal, AlertModal } from '@/components/common/Modal';
import { 
  User as UserIcon, 
  Mail, 
  Calendar, 
  Shield, 
  Save, 
  Loader2, 
  CheckCircle,
  AlertCircle,
  Key,
  Lock,
  Link2,
  Camera,
  Trash2
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface ProfileFormData {
  first_name: string;
  last_name: string;
  email: string;
}

interface PasswordFormData {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

/**
 * User Profile page component.
 * Allows users to view and edit their personal information.
 */
export default function ProfilePage() {
  const { t } = useTranslation();
  const { user, fetchUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'connections'>('profile');
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showDeleteAvatarModal, setShowDeleteAvatarModal] = useState(false);
  const [pendingProfileData, setPendingProfileData] = useState<ProfileFormData | null>(null);
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: 'success' | 'error';
  }>({ isOpen: false, title: '', message: '', variant: 'success' });
  const [isAvatarLoading, setIsAvatarLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    formState: { errors: profileErrors, isDirty: isProfileDirty },
    reset: resetProfileForm,
  } = useForm<ProfileFormData>({
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      email: user?.email || '',
    },
  });

  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    formState: { errors: passwordErrors },
    reset: resetPasswordForm,
    watch,
  } = useForm<PasswordFormData>();

  const newPassword = watch('new_password');

  // Fetch user data on mount
  useEffect(() => {
    if (!user) {
      fetchUser().catch(console.error);
    }
  }, [user, fetchUser]);

  // Update form when user data changes
  useEffect(() => {
    if (user) {
      resetProfileForm({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
      });
    }
  }, [user, resetProfileForm]);

  // Show confirmation modal before saving
  const onProfileSubmit = (data: ProfileFormData) => {
    setPendingProfileData(data);
    setShowConfirmModal(true);
  };

  // Actually save the profile after confirmation
  const handleConfirmSave = async () => {
    if (!pendingProfileData) return;
    
    setShowConfirmModal(false);
    setIsLoading(true);
    setSuccessMessage(null);
    setErrorMessage(null);

    try {
      await usersService.updateMe({
        first_name: pendingProfileData.first_name,
        last_name: pendingProfileData.last_name,
      });
      // Refresh user data in the store
      await fetchUser();
      setAlertModal({
        isOpen: true,
        title: t('common.success'),
        message: t('profile.updateSuccess'),
        variant: 'success',
      });
    } catch (error) {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: error instanceof Error ? error.message : t('profile.updateError'),
        variant: 'error',
      });
    } finally {
      setIsLoading(false);
      setPendingProfileData(null);
    }
  };

  // Handle avatar click
  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      setAlertModal({
        isOpen: true,
        title: 'Invalid File',
        message: 'Please select a valid image file (JPEG, PNG, GIF, or WebP).',
        variant: 'error',
      });
      return;
    }

    // Validate file size (5MB max)
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      setAlertModal({
        isOpen: true,
        title: 'File Too Large',
        message: 'Image must be less than 5MB.',
        variant: 'error',
      });
      return;
    }

    setIsAvatarLoading(true);
    try {
      await usersService.uploadAvatar(file);
      await fetchUser();
      setAlertModal({
        isOpen: true,
        title: 'Success',
        message: 'Avatar updated successfully!',
        variant: 'success',
      });
    } catch (error) {
      setAlertModal({
        isOpen: true,
        title: 'Error',
        message: error instanceof Error ? error.message : 'Failed to upload avatar',
        variant: 'error',
      });
    } finally {
      setIsAvatarLoading(false);
      // Reset the input so the same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Handle delete avatar confirmation
  const handleDeleteAvatar = async () => {
    setShowDeleteAvatarModal(false);
    setIsAvatarLoading(true);
    try {
      await usersService.deleteAvatar();
      await fetchUser();
      setAlertModal({
        isOpen: true,
        title: t('common.success'),
        message: t('profile.avatarDeleteSuccess'),
        variant: 'success',
      });
    } catch (error) {
      setAlertModal({
        isOpen: true,
        title: t('common.error'),
        message: error instanceof Error ? error.message : t('profile.avatarDeleteError'),
        variant: 'error',
      });
    } finally {
      setIsAvatarLoading(false);
    }
  };

  const onPasswordSubmit = async (data: PasswordFormData) => {
    setIsPasswordLoading(true);
    setSuccessMessage(null);
    setErrorMessage(null);

    try {
      // Call password change endpoint
      const response = await fetch('/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth-storage') ? JSON.parse(localStorage.getItem('auth-storage')!).state.accessToken : ''}`,
        },
        body: JSON.stringify({
          current_password: data.current_password,
          new_password: data.new_password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || 'Failed to change password');
      }

      setSuccessMessage(t('profile.passwordChangeSuccess'));
      resetPasswordForm();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('profile.passwordChangeError'));
    } finally {
      setIsPasswordLoading(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          {t('profile.title')}
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          {t('profile.subtitle')}
        </p>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center space-x-3">
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          <p className="text-sm text-green-700 dark:text-green-300">{successMessage}</p>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
        </div>
      )}

      {/* Profile Header Card */}
      <div className="card p-6">
        <div className="flex items-center space-x-6">
          {/* Avatar with upload capability */}
          <div className="relative">
            <div className="relative group">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={`${user.first_name} ${user.last_name}`}
                  className="w-20 h-20 rounded-full object-cover"
                />
              ) : (
                <div className="w-20 h-20 bg-primary-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-2xl font-bold">
                    {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
                  </span>
                </div>
              )}
              <button
                onClick={handleAvatarClick}
                disabled={isAvatarLoading}
                className="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer disabled:cursor-not-allowed"
                type="button"
                title="Change photo"
              >
                {isAvatarLoading ? (
                  <Loader2 className="w-6 h-6 text-white animate-spin" />
                ) : (
                  <Camera className="w-6 h-6 text-white" />
                )}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                onChange={handleAvatarChange}
                className="hidden"
              />
            </div>
            {/* Delete avatar button - only show if user has avatar */}
            {user?.avatar_url && (
              <button
                onClick={() => setShowDeleteAvatarModal(true)}
                disabled={isAvatarLoading}
                className="absolute -bottom-1 -right-1 w-6 h-6 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center text-white transition-colors disabled:opacity-50"
                type="button"
                title="Remove photo"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            )}
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
              {user?.first_name} {user?.last_name}
            </h2>
            <p className="text-slate-500 dark:text-slate-400">{user?.email}</p>
            <div className="flex items-center space-x-4 mt-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                user?.is_superuser 
                  ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300' 
                  : 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
              }`}>
                <Shield className="w-3 h-3 mr-1" />
                {user?.is_superuser ? t('settings.administrator') : t('settings.user')}
              </span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                user?.is_active 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' 
                  : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
              }`}>
                {user?.is_active ? t('users.active') : t('users.inactive')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('profile')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'profile'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <UserIcon className="w-4 h-4 inline-block mr-2" />
            {t('profile.tabs.profile')}
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'security'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Lock className="w-4 h-4 inline-block mr-2" />
            {t('profile.tabs.security')}
          </button>
          <button
            onClick={() => setActiveTab('connections')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'connections'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Link2 className="w-4 h-4 inline-block mr-2" />
            {t('profile.tabs.connections')}
          </button>
        </nav>
      </div>

      {/* Profile Tab Content */}
      {activeTab === 'profile' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Edit Profile Form */}
          <div className="lg:col-span-2">
            <div className="card">
              <div className="p-6 border-b border-slate-200 dark:border-slate-700">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                  {t('profile.editProfile')}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {t('profile.updatePersonalInfo')}
                </p>
              </div>
              <form onSubmit={handleProfileSubmit(onProfileSubmit)} className="p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      {t('users.firstName')}
                    </label>
                    <input
                      type="text"
                      className="input"
                      {...registerProfile('first_name', { required: t('validation.required') })}
                    />
                    {profileErrors.first_name && (
                      <p className="mt-1 text-sm text-red-600">{profileErrors.first_name.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      {t('users.lastName')}
                    </label>
                    <input
                      type="text"
                      className="input"
                      {...registerProfile('last_name', { required: t('validation.required') })}
                    />
                    {profileErrors.last_name && (
                      <p className="mt-1 text-sm text-red-600">{profileErrors.last_name.message}</p>
                    )}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {t('auth.emailAddress')}
                  </label>
                  <input
                    type="email"
                    className="input bg-slate-50 dark:bg-slate-800"
                    disabled
                    {...registerProfile('email')}
                  />
                  <p className="mt-1 text-xs text-slate-500">{t('profile.emailNoChange')}</p>
                </div>
                <div className="pt-4">
                  <button
                    type="submit"
                    disabled={isLoading || !isProfileDirty}
                    className="btn-primary"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        {t('common.loading')}
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        {t('common.save')}
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Account Info Sidebar */}
          <div className="space-y-6">
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                {t('profile.accountDetails')}
              </h3>
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Mail className="w-5 h-5 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{t('auth.emailAddress')}</p>
                    <p className="text-sm text-slate-900 dark:text-white">{user?.email}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <Calendar className="w-5 h-5 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{t('profile.memberSince')}</p>
                    <p className="text-sm text-slate-900 dark:text-white">
                      {formatDate(user?.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <Key className="w-5 h-5 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{t('profile.lastLogin')}</p>
                    <p className="text-sm text-slate-900 dark:text-white">
                      {formatDate(user?.last_login)}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* MFA Status Card */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                {t('profile.twoFactorAuth')}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                {t('profile.twoFactorDescription')}
              </p>
              <Link
                to="/security/mfa"
                className="btn-secondary w-full text-center"
              >
                <Shield className="w-4 h-4 mr-2" />
                {t('profile.configureMfa')}
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Security Tab Content */}
      {activeTab === 'security' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Change Password */}
          <div className="card">
            <div className="p-6 border-b border-slate-200 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                {t('profile.changePassword')}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {t('profile.changePasswordDescription')}
              </p>
            </div>
            <form onSubmit={handlePasswordSubmit(onPasswordSubmit)} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('profile.currentPassword')}
                </label>
                <input
                  type="password"
                  className="input"
                  {...registerPassword('current_password', { required: t('validation.required') })}
                />
                {passwordErrors.current_password && (
                  <p className="mt-1 text-sm text-red-600">{passwordErrors.current_password.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('profile.newPassword')}
                </label>
                <input
                  type="password"
                  className="input"
                  {...registerPassword('new_password', { 
                    required: t('validation.required'),
                    minLength: { value: 8, message: t('validation.passwordMin', { min: 8 }) },
                    pattern: {
                      value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                      message: t('validation.passwordStrength')
                    }
                  })}
                />
                {passwordErrors.new_password && (
                  <p className="mt-1 text-sm text-red-600">{passwordErrors.new_password.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('profile.confirmPassword')}
                </label>
                <input
                  type="password"
                  className="input"
                  {...registerPassword('confirm_password', { 
                    required: t('validation.required'),
                    validate: value => value === newPassword || t('profile.passwordsNoMatch')
                  })}
                />
                {passwordErrors.confirm_password && (
                  <p className="mt-1 text-sm text-red-600">{passwordErrors.confirm_password.message}</p>
                )}
              </div>
              <div className="pt-4">
                <button
                  type="submit"
                  disabled={isPasswordLoading}
                  className="btn-primary"
                >
                  {isPasswordLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      {t('common.loading')}
                    </>
                  ) : (
                    <>
                      <Lock className="w-4 h-4 mr-2" />
                      {t('profile.updatePassword')}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Security Options */}
          <div className="space-y-6">
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                Two-Factor Authentication
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Protect your account with an additional layer of security using TOTP.
              </p>
              <Link
                to="/security/mfa"
                className="btn-secondary w-full text-center"
              >
                <Shield className="w-4 h-4 mr-2" />
                Configure 2FA
              </Link>
            </div>

            <div className="card p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                Active Sessions
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Manage your active login sessions across devices.
              </p>
              <button
                className="btn-secondary w-full"
                onClick={() => alert('Coming soon!')}
              >
                View All Sessions
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Connected Accounts Tab Content */}
      {activeTab === 'connections' && (
        <div className="card p-6">
          <ConnectedAccounts />
        </div>
      )}

      {/* Confirm Save Modal */}
      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => {
          setShowConfirmModal(false);
          setPendingProfileData(null);
        }}
        onConfirm={handleConfirmSave}
        title={t('profile.saveChanges')}
        message={t('profile.saveChangesConfirm')}
        confirmText={isLoading ? t('common.loading') : t('common.save')}
        cancelText={t('common.cancel')}
        variant="info"
        isLoading={isLoading}
      />

      {/* Confirm Delete Avatar Modal */}
      <ConfirmModal
        isOpen={showDeleteAvatarModal}
        onClose={() => setShowDeleteAvatarModal(false)}
        onConfirm={handleDeleteAvatar}
        title={t('profile.removePhoto')}
        message={t('profile.removePhotoConfirm')}
        confirmText={isAvatarLoading ? t('common.loading') : t('profile.removePhoto')}
        cancelText={t('common.cancel')}
        variant="danger"
        isLoading={isAvatarLoading}
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
