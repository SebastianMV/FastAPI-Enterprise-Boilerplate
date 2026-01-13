import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { auditLogsService, type AuditLog, type AuditLogFilters } from '@/services/api';
import {
  Shield,
  Search,
  Filter,
  RefreshCw,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye,
  User,
  Clock,
  Globe,
  FileText,
  LogIn,
  LogOut,
  AlertTriangle,
  Key,
  Trash2,
  Edit,
  Plus,
} from 'lucide-react';
import { Modal } from '@/components/common/Modal';

// Action type icons
const actionIcons: Record<string, typeof Shield> = {
  CREATE: Plus,
  READ: Eye,
  UPDATE: Edit,
  DELETE: Trash2,
  LOGIN: LogIn,
  LOGOUT: LogOut,
  LOGIN_FAILED: AlertTriangle,
  PASSWORD_CHANGE: Key,
  PASSWORD_RESET: Key,
  MFA_ENABLED: Shield,
  MFA_DISABLED: Shield,
  API_KEY_CREATED: Key,
  API_KEY_REVOKED: Key,
};

// Action type colors
const actionColors: Record<string, string> = {
  CREATE: 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400',
  READ: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400',
  UPDATE: 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400',
  DELETE: 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400',
  LOGIN: 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400',
  LOGOUT: 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-400',
  LOGIN_FAILED: 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400',
};

/**
 * Audit Log viewer page for security and compliance.
 */
export default function AuditLogPage() {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<AuditLogFilters>({
    skip: 0,
    limit: 25,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Fetch audit logs
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['auditLogs', filters],
    queryFn: () => auditLogsService.list(filters),
  });

  // Fetch available actions for filter
  const { data: actions } = useQuery({
    queryKey: ['auditActions'],
    queryFn: () => auditLogsService.getActions(),
  });

  // Fetch available resource types for filter
  const { data: resourceTypes } = useQuery({
    queryKey: ['auditResourceTypes'],
    queryFn: () => auditLogsService.getResourceTypes(),
  });

  // Handle page change
  const handlePageChange = (direction: 'prev' | 'next') => {
    const newSkip = direction === 'next' 
      ? (filters.skip || 0) + (filters.limit || 25)
      : Math.max(0, (filters.skip || 0) - (filters.limit || 25));
    setFilters({ ...filters, skip: newSkip });
  };

  // Calculate pagination info
  const currentPage = Math.floor((filters.skip || 0) / (filters.limit || 25)) + 1;
  const totalPages = data ? Math.ceil(data.total / (filters.limit || 25)) : 0;

  // View log details
  const viewLogDetails = (log: AuditLog) => {
    setSelectedLog(log);
    setShowDetailModal(true);
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  // Get action icon
  const getActionIcon = (action: string) => {
    const IconComponent = actionIcons[action] || FileText;
    return IconComponent;
  };

  // Get action color
  const getActionColor = (action: string) => {
    return actionColors[action] || 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-400';
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-500 mb-4">Failed to load audit logs</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
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
          {t('audit.title')}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Security and compliance activity log
        </p>
      </div>

      {/* Actions bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        {/* Search and filters */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder={t('audit.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center px-3 py-2 border rounded-md transition-colors ${
              showFilters
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-600'
                : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300'
            }`}
          >
            <Filter className="h-4 w-4 mr-2" />
            {t('audit.filters')}
          </button>
        </div>

        {/* Refresh button */}
        <button
          onClick={() => refetch()}
          className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          {t('audit.refreshLogs')}
        </button>
      </div>

      {/* Filters panel */}
      {showFilters && (
        <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Action filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('audit.filter.actionType')}
              </label>
              <select
                value={filters.action || ''}
                onChange={(e) => setFilters({ ...filters, action: e.target.value || undefined, skip: 0 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="">{t('audit.filter.allActions')}</option>
                {actions?.map((action) => (
                  <option key={action} value={action}>
                    {action.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('audit.filter.resourceType')}
              </label>
              <select
                value={filters.resource_type || ''}
                onChange={(e) => setFilters({ ...filters, resource_type: e.target.value || undefined, skip: 0 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="">{t('audit.filter.allTypes')}</option>
                {resourceTypes?.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('audit.filter.startDate')}
              </label>
              <input
                type="date"
                value={filters.start_date?.split('T')[0] || ''}
                onChange={(e) => setFilters({ ...filters, start_date: e.target.value ? `${e.target.value}T00:00:00Z` : undefined, skip: 0 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('audit.filter.endDate')}
              </label>
              <input
                type="date"
                value={filters.end_date?.split('T')[0] || ''}
                onChange={(e) => setFilters({ ...filters, end_date: e.target.value ? `${e.target.value}T23:59:59Z` : undefined, skip: 0 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={() => setFilters({ skip: 0, limit: 25 })}
              className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              {t('audit.filter.clearAll')}
            </button>
          </div>
        </div>
      )}

      {/* Logs table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {t('audit.table.timestamp')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {t('audit.table.action')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {t('audit.table.actor')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {t('audit.table.resource')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {t('audit.table.ipAddress')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {t('common.actions')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {data?.items?.map((log) => {
                  const ActionIcon = getActionIcon(log.action);
                  return (
                    <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center text-sm text-gray-600 dark:text-gray-300">
                          <Clock className="h-4 w-4 mr-2 text-gray-400" />
                          {formatTimestamp(log.timestamp)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getActionColor(log.action)}`}>
                          <ActionIcon className="h-3 w-3 mr-1" />
                          {log.action.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <User className="h-4 w-4 mr-2 text-gray-400" />
                          <span className="text-sm text-gray-900 dark:text-white">
                            {log.actor_email || 'System'}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm">
                          <span className="text-gray-500 dark:text-gray-400">
                            {log.resource_type}
                          </span>
                          {log.resource_name && (
                            <span className="ml-2 text-gray-900 dark:text-white">
                              {log.resource_name}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                          <Globe className="h-4 w-4 mr-2" />
                          {log.actor_ip || 'N/A'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <button
                          onClick={() => viewLogDetails(log)}
                          className="text-blue-600 hover:text-blue-700 dark:text-blue-400"
                          title="View details"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}

                {data?.items?.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                      <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p className="text-lg font-medium">{t('audit.noLogsFound')}</p>
                      <p className="text-sm">{t('audit.tryAdjustingFilters')}</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {data && data.total > 0 && (
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {t('audit.pagination.showing')} {(filters.skip || 0) + 1} {t('audit.pagination.to')} {Math.min((filters.skip || 0) + (filters.limit || 25), data.total)} {t('audit.pagination.of')} {data.total} {t('audit.pagination.entries')}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange('prev')}
                  disabled={currentPage === 1}
                  className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  {t('audit.pagination.previous')}
                </button>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {t('audit.pagination.page')} {currentPage} {t('audit.pagination.of')} {totalPages}
                </span>
                <button
                  onClick={() => handlePageChange('next')}
                  disabled={currentPage >= totalPages}
                  className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('audit.pagination.next')}
                  <ChevronRight className="h-4 w-4 ml-1" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Detail Modal */}
      <Modal
        isOpen={showDetailModal}
        onClose={() => {
          setShowDetailModal(false);
          setSelectedLog(null);
        }}
        title="Audit Log Details"
      >
        {selectedLog && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">ID</label>
                <p className="text-sm text-gray-900 dark:text-white font-mono">{selectedLog.id}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">Timestamp</label>
                <p className="text-sm text-gray-900 dark:text-white">{formatTimestamp(selectedLog.timestamp)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">Action</label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedLog.action}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">Resource Type</label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedLog.resource_type}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">Actor Email</label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedLog.actor_email || 'System'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">IP Address</label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedLog.actor_ip || 'N/A'}</p>
              </div>
            </div>

            {selectedLog.resource_name && (
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">Resource Name</label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedLog.resource_name}</p>
              </div>
            )}

            {selectedLog.reason && (
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">Reason</label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedLog.reason}</p>
              </div>
            )}

            {selectedLog.actor_user_agent && (
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">User Agent</label>
                <p className="text-sm text-gray-900 dark:text-white break-all">{selectedLog.actor_user_agent}</p>
              </div>
            )}

            {(selectedLog.old_value || selectedLog.new_value) && (
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Changes</h4>
                <div className="grid grid-cols-2 gap-4">
                  {selectedLog.old_value && (
                    <div>
                      <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">Before</label>
                      <pre className="mt-1 p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs overflow-auto max-h-40">
                        {JSON.stringify(selectedLog.old_value, null, 2)}
                      </pre>
                    </div>
                  )}
                  {selectedLog.new_value && (
                    <div>
                      <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">After</label>
                      <pre className="mt-1 p-2 bg-green-50 dark:bg-green-900/20 rounded text-xs overflow-auto max-h-40">
                        {JSON.stringify(selectedLog.new_value, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}

            {Object.keys(selectedLog.metadata).length > 0 && (
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                <label className="text-xs text-gray-500 dark:text-gray-400 uppercase">Metadata</label>
                <pre className="mt-1 p-2 bg-gray-100 dark:bg-gray-900 rounded text-xs overflow-auto max-h-40">
                  {JSON.stringify(selectedLog.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
