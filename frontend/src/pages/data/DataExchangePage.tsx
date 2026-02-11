import { useState, useEffect, useCallback, type ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Download,
  Upload,
  FileBarChart,
  FolderOpen,
  Table,
  CheckCircle,
  XCircle,
  FileDown,
} from 'lucide-react';
import {
  dataExchangeService,
  type Entity,
  type EntityField,
  type ExportPreview,
  type ImportResult,
} from '../../services/api';

type TabType = 'export' | 'import' | 'reports';

export default function DataExchangePage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabType>('export');
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Export state
  const [exportFormat, setExportFormat] = useState<'csv' | 'excel' | 'json'>('csv');
  const [exportPreview, setExportPreview] = useState<ExportPreview | null>(null);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);

  // Import state
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importMode, setImportMode] = useState<'insert' | 'update' | 'upsert'>('upsert');
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [validating, setValidating] = useState(false);

  // Report state
  const [reportFormat, setReportFormat] = useState<'pdf' | 'excel' | 'csv'>('pdf');
  const [reportTitle, setReportTitle] = useState('');

  const loadEntities = useCallback(async () => {
    try {
      setLoading(true);
      const data = await dataExchangeService.listEntities();
      setEntities(data);
      if (data.length > 0) {
        setSelectedEntity(data[0].name);
      }
    } catch (err) {
      setError(t('data.loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  // Load entities on mount
  useEffect(() => {
    loadEntities();
  }, [loadEntities]);

  const loadExportPreview = useCallback(async () => {
    if (!selectedEntity) return;
    
    try {
      setLoading(true);
      const preview = await dataExchangeService.previewExport(selectedEntity, 5);
      setExportPreview(preview);
    } catch {
      // Preview failed — non-critical, don't log error details
    } finally {
      setLoading(false);
    }
  }, [selectedEntity]);

  useEffect(() => {
    if (activeTab === 'export' && selectedEntity) {
      loadExportPreview();
    }
  }, [activeTab, selectedEntity, loadExportPreview]);

  const handleExport = async () => {
    if (!selectedEntity) return;
    
    try {
      setLoading(true);
      const blob = await dataExchangeService.exportData(
        selectedEntity,
        exportFormat,
        selectedColumns.length > 0 ? selectedColumns : undefined
      );
      
      // Download file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedEntity}_export.${exportFormat === 'excel' ? 'xlsx' : exportFormat}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => window.URL.revokeObjectURL(url), 100);
    } catch (err) {
      setError(t('data.exportError'));
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadTemplate = async () => {
    if (!selectedEntity) return;
    
    try {
      setLoading(true);
      const blob = await dataExchangeService.downloadTemplate(selectedEntity, 'csv');
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedEntity}_template.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => window.URL.revokeObjectURL(url), 100);
    } catch (err) {
      setError(t('data.templateError'));
    } finally {
      setLoading(false);
    }
  };

  const handleValidateImport = async () => {
    if (!selectedEntity || !importFile) return;
    
    try {
      setValidating(true);
      setImportResult(null);
      const result = await dataExchangeService.validateImport(selectedEntity, importFile);
      setImportResult(result);
    } catch (err) {
      setError(t('data.validateError'));
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    if (!selectedEntity || !importFile) return;
    
    try {
      setLoading(true);
      setImportResult(null);
      const result = await dataExchangeService.importData(selectedEntity, importFile, importMode);
      setImportResult(result);
      
      if (result.success) {
        setImportFile(null);
      }
    } catch (err) {
      setError(t('data.importError'));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedEntity) return;
    
    try {
      setLoading(true);
      const blob = await dataExchangeService.generateReport(selectedEntity, {
        title: reportTitle || t('data.reportTitle', { entity: selectedEntity }),
        format: reportFormat,
        include_summary: true,
      });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedEntity}_report.${reportFormat === 'excel' ? 'xlsx' : reportFormat}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => window.URL.revokeObjectURL(url), 100);
    } catch (err) {
      setError(t('data.reportError'));
    } finally {
      setLoading(false);
    }
  };

  const selectedEntityData = entities.find((e: Entity) => e.name === selectedEntity);

  const tabs = [
    { id: 'export' as const, name: t('data.export'), icon: Download },
    { id: 'import' as const, name: t('data.import'), icon: Upload },
    { id: 'reports' as const, name: t('data.reports'), icon: FileBarChart },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('data.title')}
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {t('data.description')}
          </p>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
          <div className="flex">
            <XCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-500"
            >
              <span className="sr-only">{t('profile.emailVerification.dismiss')}</span>
              <XCircle className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Entity Selector */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {t('data.selectEntity')}
        </label>
        <div className="flex items-center gap-4">
          <FolderOpen className="h-5 w-5 text-gray-400" />
          <select
            value={selectedEntity}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedEntity(e.target.value)}
            className="block w-full max-w-xs rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 py-2 px-3"
          >
            {entities.map((entity: Entity) => (
              <option key={entity.name} value={entity.name} className="text-gray-900 dark:text-white bg-white dark:bg-gray-700">
                {entity.display_name}
              </option>
            ))}
          </select>
          {selectedEntityData && (
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {selectedEntityData.fields.length} {t('data.fields')}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8 px-6" aria-label={t('data.tabNavigation')}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium
                  ${activeTab === tab.id
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                  }
                `}
              >
                <tab.icon className="h-5 w-5" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Export Tab */}
          {activeTab === 'export' && (
            <div className="space-y-6">
              {/* Format Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('data.exportFormat')}
                </label>
                <div className="flex gap-4">
                  {(['csv', 'excel', 'json'] as const).map((format) => (
                    <label key={format} className="flex items-center">
                      <input
                        type="radio"
                        value={format}
                        checked={exportFormat === format}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setExportFormat(e.target.value as typeof exportFormat)}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300 uppercase">
                        {format}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Column Selection */}
              {selectedEntityData && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {t('data.selectColumns')}
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {selectedEntityData.fields
                      .filter((f: EntityField) => f.exportable)
                      .map((field: EntityField) => (
                        <label
                          key={field.name}
                          className={`
                            inline-flex items-center px-3 py-1.5 rounded-full text-sm cursor-pointer
                            ${selectedColumns.includes(field.name)
                              ? 'bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300'
                              : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                            }
                          `}
                        >
                          <input
                            type="checkbox"
                            checked={selectedColumns.includes(field.name)}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => {
                              if (e.target.checked) {
                                setSelectedColumns([...selectedColumns, field.name]);
                              } else {
                                setSelectedColumns(selectedColumns.filter((c: string) => c !== field.name));
                              }
                            }}
                            className="sr-only"
                          />
                          {field.display_name}
                        </label>
                      ))}
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {selectedColumns.length === 0
                      ? t('data.allColumnsSelected')
                      : t('data.columnsSelected', { count: selectedColumns.length })}
                  </p>
                </div>
              )}

              {/* Preview */}
              {exportPreview && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {t('data.preview')} ({exportPreview.total_count} {t('data.records')})
                  </h3>
                  <div className="overflow-x-auto border rounded-lg dark:border-gray-700">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                          {exportPreview.rows.length > 0 &&
                            Object.keys(exportPreview.rows[0]).map((key: string) => (
                              <th
                                key={key}
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase"
                              >
                                {key}
                              </th>
                            ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                        {exportPreview.rows.map((row: Record<string, unknown>, idx: number) => (
                          <tr key={idx}>
                            {Object.values(row).map((value: unknown, vidx: number) => (
                              <td
                                key={vidx}
                                className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100 whitespace-nowrap"
                              >
                                {String(value ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Export Button */}
              <button
                onClick={handleExport}
                disabled={loading || !selectedEntity}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
              >
                <Download className="h-5 w-5 mr-2" />
                {loading ? t('common.loading') : t('data.exportButton')}
              </button>
            </div>
          )}

          {/* Import Tab */}
          {activeTab === 'import' && (
            <div className="space-y-6">
              {/* Download Template */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                    {t('data.downloadTemplate')}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t('data.templateDescription')}
                  </p>
                </div>
                <button
                  onClick={handleDownloadTemplate}
                  disabled={loading}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <FileDown className="h-5 w-5 mr-2" />
                  {t('data.downloadTemplateButton')}
                </button>
              </div>

              {/* Import Mode */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('data.importMode')}
                </label>
                <div className="flex gap-4">
                  {(['insert', 'update', 'upsert'] as const).map((mode) => (
                    <label key={mode} className="flex items-center">
                      <input
                        type="radio"
                        value={mode}
                        checked={importMode === mode}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setImportMode(e.target.value as typeof importMode)}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300 capitalize">
                        {t(`data.mode.${mode}`)}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('data.uploadFile')}
                </label>
                <div className="flex items-center gap-4">
                  <label className="flex items-center justify-center w-full max-w-lg h-32 px-4 transition bg-white dark:bg-gray-900 border-2 border-gray-300 dark:border-gray-600 border-dashed rounded-lg cursor-pointer hover:border-primary-500">
                    <div className="flex flex-col items-center">
                      <Upload className="w-8 h-8 text-gray-400" />
                      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        {importFile ? importFile.name : t('data.dropFileHere')}
                      </p>
                      <p className="text-xs text-gray-400">{t('data.acceptedFormats')}</p>
                    </div>
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={(e: ChangeEvent<HTMLInputElement>) => {
                        const file = e.target.files?.[0] || null;
                        const MAX_FILE_SIZE_MB = 50;
                        if (file && file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
                          setError(t('data.fileTooLarge', { maxSize: MAX_FILE_SIZE_MB }));
                          e.target.value = '';
                          return;
                        }
                        setImportFile(file);
                        setImportResult(null);
                      }}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>

              {/* Validation & Import Buttons */}
              <div className="flex gap-4">
                <button
                  onClick={handleValidateImport}
                  disabled={validating || !importFile}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                >
                  <Table className="h-5 w-5 mr-2" />
                  {validating ? t('common.loading') : t('data.validateButton')}
                </button>
                <button
                  onClick={handleImport}
                  disabled={loading || !importFile}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                >
                  <Upload className="h-5 w-5 mr-2" />
                  {loading ? t('common.loading') : t('data.importButton')}
                </button>
              </div>

              {/* Import Result */}
              {importResult && (
                <div className={`rounded-lg p-4 ${
                  importResult.success
                    ? 'bg-green-50 dark:bg-green-900/20'
                    : 'bg-red-50 dark:bg-red-900/20'
                }`}>
                  <div className="flex items-start">
                    {importResult.success ? (
                      <CheckCircle className="h-5 w-5 text-green-400" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-400" />
                    )}
                    <div className="ml-3 flex-1">
                      <h3 className={`text-sm font-medium ${
                        importResult.success
                          ? 'text-green-800 dark:text-green-300'
                          : 'text-red-800 dark:text-red-300'
                      }`}>
                        {importResult.dry_run ? t('data.validationResult') : t('data.importResult')}
                      </h3>
                      <div className="mt-2 text-sm">
                        <ul className="list-disc pl-5 space-y-1">
                          <li>{t('data.totalRows')}: {importResult.total_rows}</li>
                          <li>{t('data.inserted')}: {importResult.inserted}</li>
                          <li>{t('data.updated')}: {importResult.updated}</li>
                          <li>{t('data.skipped')}: {importResult.skipped}</li>
                          <li>{t('data.errors')}: {importResult.error_count}</li>
                        </ul>
                      </div>
                      {importResult.errors.length > 0 && (
                        <div className="mt-3">
                          <h4 className="text-sm font-medium text-red-700 dark:text-red-400">
                            {t('data.errorDetails')}:
                          </h4>
                          <ul className="mt-1 text-sm text-red-600 dark:text-red-400">
                            {importResult.errors.slice(0, 5).map((err, idx) => (
                              <li key={idx}>
                                {t('data.importRowError', { row: err.row, field: err.field })}
                              </li>
                            ))}
                            {importResult.errors.length > 5 && (
                              <li>{t('data.moreErrors', { count: importResult.errors.length - 5 })}</li>
                            )}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Reports Tab */}
          {activeTab === 'reports' && (
            <div className="space-y-6">
              {/* Report Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('data.reportTitleLabel')}
                </label>
                <input
                  type="text"
                  value={reportTitle}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setReportTitle(e.target.value)}
                  placeholder={t('data.reportPlaceholder', { entity: selectedEntityData?.display_name || selectedEntity })}
                  className="block w-full max-w-md rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
              </div>

              {/* Report Format */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('data.reportFormat')}
                </label>
                <div className="flex gap-4">
                  {(['pdf', 'excel', 'csv'] as const).map((format) => (
                    <label key={format} className="flex items-center">
                      <input
                        type="radio"
                        value={format}
                        checked={reportFormat === format}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setReportFormat(e.target.value as typeof reportFormat)}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300 uppercase">
                        {format}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Entity Info */}
              {selectedEntityData && (
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                    {t('data.availableFields')}
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedEntityData.fields.map((field: EntityField) => (
                      <span
                        key={field.name}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                      >
                        {field.display_name}
                        <span className="ml-1 text-gray-400">({field.field_type})</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Generate Button */}
              <button
                onClick={handleGenerateReport}
                disabled={loading || !selectedEntity}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
              >
                <FileBarChart className="h-5 w-5 mr-2" />
                {loading ? t('common.loading') : t('data.generateReportButton')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
