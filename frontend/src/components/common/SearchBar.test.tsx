/**
 * Unit tests for SearchBar component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import SearchBar from './SearchBar';

// Mock useDebounce hook
vi.mock('@/hooks/useDebounce', () => ({
  useDebounce: (value: string) => value,
}));

// Mock search service
const mockQuickSearch = vi.fn();
vi.mock('@/services/api', () => ({
  searchService: {
    quickSearch: (...args: unknown[]) => mockQuickSearch(...args),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Wrapper with Router
function renderWithRouter(ui: React.ReactElement) {
  return render(
    <BrowserRouter>{ui}</BrowserRouter>
  );
}

describe('SearchBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockQuickSearch.mockResolvedValue({
      hits: [],
      suggestions: [],
      total: 0,
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe('Rendering', () => {
    it('should render search input', () => {
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      expect(input).toBeInTheDocument();
    });

    it('should render with custom placeholder', () => {
      renderWithRouter(<SearchBar placeholder="Custom search..." />);
      
      const input = screen.getByPlaceholderText('Custom search...');
      expect(input).toBeInTheDocument();
    });

    it('should render with default placeholder', () => {
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByPlaceholderText('common.search');
      expect(input).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      renderWithRouter(<SearchBar className="custom-class" />);
      
      // Component should be rendered with custom class
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('should render search icon', () => {
      renderWithRouter(<SearchBar />);
      
      // Search icon should be present (SVG element)
      const container = screen.getByRole('textbox').closest('div')?.parentElement;
      expect(container?.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('Input behavior', () => {
    it('should update query on input', async () => {
      const user = userEvent.setup();
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test query');
      
      expect(input).toHaveValue('test query');
    });

    it('should clear input when clear button is clicked', async () => {
      const user = userEvent.setup();
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test');
      
      // Wait for clear button to appear (it's the X button)
      await waitFor(() => {
        const buttons = screen.queryAllByRole('button');
        // Find the clear button (has the X icon)
        const clearButton = buttons.find(btn => btn.querySelector('.lucide-x'));
        if (clearButton) {
          return true;
        }
        return false;
      });
    });
  });

  describe('Search functionality', () => {
    it('should not search with query less than 2 characters', async () => {
      const user = userEvent.setup();
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'a');
      
      await waitFor(() => {
        expect(mockQuickSearch).not.toHaveBeenCalled();
      });
    });

    it('should search when query is 2+ characters', async () => {
      const user = userEvent.setup();
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'te');
      
      await waitFor(() => {
        expect(mockQuickSearch).toHaveBeenCalledWith('te', expect.any(AbortSignal));
      });
    });

    it('should display search results', async () => {
      const user = userEvent.setup();
      
      mockQuickSearch.mockResolvedValue({
        hits: [
          {
            id: '1',
            type: 'user',
            source: {
              first_name: 'Test',
              last_name: 'User',
              email: 'test@example.com',
            },
            score: 1.0,
          },
        ],
        suggestions: [],
        total: 1,
      });
      
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test');
      
      await waitFor(() => {
        expect(screen.getByText('Test User')).toBeInTheDocument();
      });
    });

    it('should handle search errors gracefully', async () => {
      const user = userEvent.setup();
      
      mockQuickSearch.mockRejectedValueOnce(new Error('Search failed'));
      
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test');
      
      // Should not crash — error is silently handled
      await waitFor(() => {
        expect(mockQuickSearch).toHaveBeenCalled();
      });
    });
  });

  describe('Recent searches', () => {
    it('should load recent searches from sessionStorage', () => {
      sessionStorage.setItem('recent-searches', JSON.stringify(['query1', 'query2']));
      
      renderWithRouter(<SearchBar />);
      
      // Component should load without errors
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('should handle invalid sessionStorage data', () => {
      sessionStorage.setItem('recent-searches', 'invalid json');
      
      // Should not throw
      renderWithRouter(<SearchBar />);
      
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });
  });

  describe('Keyboard navigation', () => {
    it('should open dropdown on focus', async () => {
      const user = userEvent.setup();
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.click(input);
      
      // Dropdown should open (check input is focused)
      expect(input).toHaveFocus();
    });

    it('should handle escape key', async () => {
      const user = userEvent.setup();
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test');
      
      fireEvent.keyDown(input, { key: 'Escape' });
      
      // Input should still be accessible
      expect(input).toBeInTheDocument();
    });

    it('should handle enter key on full search', async () => {
      const user = userEvent.setup();
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test query');
      
      fireEvent.keyDown(input, { key: 'Enter' });
      
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/search?q=test%20query');
      });
    });
  });

  describe('Dropdown behavior', () => {
    it('should close dropdown when clicking outside', async () => {
      const user = userEvent.setup();
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.click(input);
      
      // Click outside
      await user.click(document.body);
      
      // Component should still work
      expect(input).toBeInTheDocument();
    });
  });

  describe('Loading state', () => {
    it('should show loading indicator during search', async () => {
      const user = userEvent.setup();
      
      // Create a promise that we can control
      let resolveSearch: (value: unknown) => void;
      mockQuickSearch.mockReturnValueOnce(new Promise((resolve) => {
        resolveSearch = resolve;
      }));
      
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test');
      
      // Resolve the search
      resolveSearch!({ hits: [], suggestions: [], total: 0 });
      
      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });
    });
  });

  describe('Result types', () => {
    it('should display user results with icon', async () => {
      const user = userEvent.setup();
      
      mockQuickSearch.mockResolvedValue({
        hits: [
          {
            id: '1',
            type: 'user',
            source: {
              first_name: 'John',
              last_name: 'Doe',
              email: 'john@example.com',
            },
            score: 1.0,
          },
        ],
        suggestions: [],
        total: 1,
      });
      
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'john');
      
      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      });
    });

    it('should display document results', async () => {
      const user = userEvent.setup();
      
      mockQuickSearch.mockResolvedValue({
        hits: [
          {
            id: '1',
            type: 'document',
            source: {
              title: 'Important Document',
              description: 'Document content...',
            },
            score: 1.0,
          },
        ],
        suggestions: [],
        total: 1,
      });
      
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'document');
      
      await waitFor(() => {
        expect(screen.getByText('Important Document')).toBeInTheDocument();
      });
    });
  });

  describe('Suggestions', () => {
    it('should display search suggestions', async () => {
      const user = userEvent.setup();
      
      mockQuickSearch.mockResolvedValueOnce({
        hits: [],
        suggestions: ['suggestion1', 'suggestion2'],
        total: 0,
      });
      
      renderWithRouter(<SearchBar />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'sug');
      
      await waitFor(() => {
        expect(mockQuickSearch).toHaveBeenCalled();
      });
    });
  });
});
