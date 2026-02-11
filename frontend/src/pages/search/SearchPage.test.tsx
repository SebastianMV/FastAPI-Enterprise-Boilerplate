import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SearchPage from './SearchPage';

const mockQuickSearch = vi.fn();
const mockSearch = vi.fn();

vi.mock('@/services/api', () => ({
  searchService: {
    quickSearch: (...args: unknown[]) => mockQuickSearch(...args),
    search: (...args: unknown[]) => mockSearch(...args),
  },
}));

const mockSearchResults = {
  total: 2,
  page: 1,
  total_pages: 1,
  has_previous: false,
  has_next: false,
  took_ms: 15.5,
  hits: [
    {
      id: 'h1',
      score: 0.95,
      source: { first_name: 'John', last_name: 'Doe', email: 'john@test.com', created_at: '2024-01-01T00:00:00Z' },
      highlights: { email: ['<em>john</em>@test.com'] },
    },
    {
      id: 'h2',
      score: 0.8,
      source: { title: 'Test Document', content: 'This is test content about something', created_at: '2024-02-01T00:00:00Z' },
      highlights: {},
    },
  ],
};

function renderPage(initialSearch = '') {
  const path = initialSearch ? `/?q=${initialSearch}` : '/';
  return render(
    <MemoryRouter initialEntries={[path]}>
      <SearchPage />
    </MemoryRouter>,
  );
}

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockQuickSearch.mockResolvedValue(mockSearchResults);
    mockSearch.mockResolvedValue(mockSearchResults);
  });

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('search.title')).toBeInTheDocument();
  });

  it('shows empty state when no query', () => {
    renderPage();
    expect(screen.getByText('search.startSearching')).toBeInTheDocument();
  });

  it('shows search input', () => {
    renderPage();
    expect(screen.getByPlaceholderText('search.searchPlaceholder')).toBeInTheDocument();
  });

  it('shows index tabs', () => {
    renderPage();
    expect(screen.getByText('search.indexes.all')).toBeInTheDocument();
    expect(screen.getByText('search.indexes.users')).toBeInTheDocument();
    expect(screen.getByText('search.indexes.documents')).toBeInTheDocument();
  });

  it('toggles filter panel', () => {
    renderPage();
    fireEvent.click(screen.getByText('search.filters'));
    expect(screen.getByText('search.dateRange')).toBeInTheDocument();
    expect(screen.getByText('search.sortBy')).toBeInTheDocument();
  });

  it('performs search and shows results', async () => {
    renderPage();
    const input = screen.getByPlaceholderText('search.searchPlaceholder');
    fireEvent.change(input, { target: { value: 'john' } });
    
    await waitFor(() => {
      expect(mockQuickSearch).toHaveBeenCalledWith('john', expect.any(AbortSignal));
    });
    
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });

  it('shows result types', async () => {
    renderPage();
    const input = screen.getByPlaceholderText('search.searchPlaceholder');
    fireEvent.change(input, { target: { value: 'test' } });
    
    await waitFor(() => {
      expect(screen.getByText('search.resultTypes.user')).toBeInTheDocument();
    });
    expect(screen.getByText('search.resultTypes.document')).toBeInTheDocument();
  });

  it('shows results summary', async () => {
    renderPage();
    const input = screen.getByPlaceholderText('search.searchPlaceholder');
    fireEvent.change(input, { target: { value: 'test' } });
    
    await waitFor(() => {
      expect(screen.getByText(/search.resultsFound/)).toBeInTheDocument();
    });
  });

  it('shows no results state', async () => {
    mockQuickSearch.mockResolvedValue({ total: 0, hits: [], page: 1, total_pages: 0, has_previous: false, has_next: false, took_ms: 5 });
    renderPage();
    const input = screen.getByPlaceholderText('search.searchPlaceholder');
    fireEvent.change(input, { target: { value: 'nonexistent' } });
    
    await waitFor(() => {
      expect(screen.getByText('search.noResults')).toBeInTheDocument();
    });
  });

  it('shows highlights when available', async () => {
    renderPage();
    const input = screen.getByPlaceholderText('search.searchPlaceholder');
    fireEvent.change(input, { target: { value: 'john' } });
    
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });
    // Highlight fragment should be rendered inside an italic element
    const italicElements = document.querySelectorAll('p.italic');
    expect(italicElements.length).toBeGreaterThanOrEqual(1);
  });
});
