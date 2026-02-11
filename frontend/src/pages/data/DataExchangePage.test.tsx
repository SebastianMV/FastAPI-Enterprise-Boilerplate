import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DataExchangePage from './DataExchangePage';

const mockListEntities = vi.fn();
const mockPreviewExport = vi.fn();
const mockExportData = vi.fn();
const mockDownloadTemplate = vi.fn();
const mockValidateImport = vi.fn();
const mockImportData = vi.fn();
const mockGenerateReport = vi.fn();

vi.mock('../../services/api', () => ({
  dataExchangeService: {
    listEntities: (...args: unknown[]) => mockListEntities(...args),
    previewExport: (...args: unknown[]) => mockPreviewExport(...args),
    exportData: (...args: unknown[]) => mockExportData(...args),
    downloadTemplate: (...args: unknown[]) => mockDownloadTemplate(...args),
    validateImport: (...args: unknown[]) => mockValidateImport(...args),
    importData: (...args: unknown[]) => mockImportData(...args),
    generateReport: (...args: unknown[]) => mockGenerateReport(...args),
  },
}));

const mockEntities = [
  {
    name: 'users',
    display_name: 'Users',
    fields: [
      { name: 'email', display_name: 'Email', field_type: 'string', exportable: true },
      { name: 'name', display_name: 'Name', field_type: 'string', exportable: true },
      { name: 'id', display_name: 'ID', field_type: 'uuid', exportable: false },
    ],
  },
  {
    name: 'roles',
    display_name: 'Roles',
    fields: [
      { name: 'name', display_name: 'Name', field_type: 'string', exportable: true },
    ],
  },
];

const mockPreview = {
  total_count: 10,
  rows: [
    { email: 'test@test.com', name: 'Test User' },
    { email: 'admin@test.com', name: 'Admin User' },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DataExchangePage />
    </MemoryRouter>,
  );
}

describe('DataExchangePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListEntities.mockResolvedValue(mockEntities);
    mockPreviewExport.mockResolvedValue(mockPreview);
  });

  it('renders page title', async () => {
    renderPage();
    expect(screen.getByText('data.title')).toBeInTheDocument();
  });

  it('loads entities on mount', async () => {
    renderPage();
    await waitFor(() => {
      expect(mockListEntities).toHaveBeenCalled();
    });
  });

  it('shows entity selector with loaded entities', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Users')).toBeInTheDocument();
    });
  });

  it('shows export tab by default', async () => {
    renderPage();
    expect(screen.getByText('data.exportFormat')).toBeInTheDocument();
  });

  it('shows format radio buttons on export tab', async () => {
    renderPage();
    expect(screen.getByText('csv')).toBeInTheDocument();
    expect(screen.getByText('excel')).toBeInTheDocument();
    expect(screen.getByText('json')).toBeInTheDocument();
  });

  it('shows export preview after loading', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('test@test.com')).toBeInTheDocument();
    });
    expect(screen.getByText('Admin User')).toBeInTheDocument();
  });

  it('shows column selection for exportable fields', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Email')).toBeInTheDocument();
    });
    expect(screen.getByText('Name')).toBeInTheDocument();
  });

  it('switches to import tab', async () => {
    renderPage();
    await waitFor(() => {
      expect(mockListEntities).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByText('data.import'));
    expect(screen.getByText('data.downloadTemplate')).toBeInTheDocument();
    expect(screen.getByText('data.importMode')).toBeInTheDocument();
  });

  it('shows import mode options', async () => {
    renderPage();
    fireEvent.click(screen.getByText('data.import'));
    expect(screen.getByText('data.mode.insert')).toBeInTheDocument();
    expect(screen.getByText('data.mode.update')).toBeInTheDocument();
    expect(screen.getByText('data.mode.upsert')).toBeInTheDocument();
  });

  it('switches to reports tab', async () => {
    renderPage();
    fireEvent.click(screen.getByText('data.reports'));
    expect(screen.getByText('data.reportTitleLabel')).toBeInTheDocument();
    expect(screen.getByText('data.reportFormat')).toBeInTheDocument();
  });

  it('shows error alert and allows dismiss', async () => {
    mockListEntities.mockRejectedValue(new Error('Fail'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('data.loadError')).toBeInTheDocument();
    });
  });

  it('shows field count for selected entity', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('3 data.fields')).toBeInTheDocument();
    });
  });
});
