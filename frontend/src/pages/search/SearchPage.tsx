import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  Search,
  User, 
  FileText, 
  MessageSquare, 
  Calendar,
  ChevronLeft,
  ChevronRight,
  Loader2,
  SlidersHorizontal,
  X
} from 'lucide-react';
import { searchService, type SearchResponse, type SearchRequest } from '@/services/api';

type SearchIndex = 'users' | 'documents' | 'messages' | 'all';

interface FilterState {
  index: SearchIndex;
  dateRange: 'any' | 'day' | 'week' | 'month' | 'year';
  sortBy: 'relevance' | 'date' | 'name';
}

/**
 * Search results page with filters and pagination.
 */
export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialQuery = searchParams.get('q') || '';
  const initialIndex = (searchParams.get('index') || 'all') as SearchIndex;
  const initialPage = parseInt(searchParams.get('page') || '1', 10);

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    index: initialIndex,
    dateRange: 'any',
    sortBy: 'relevance',
  });
  const [page, setPage] = useState(initialPage);

  // Perform search
  useEffect(() => {
    const performSearch = async () => {
      if (!query) {
        setResults(null);
        return;
      }

      setIsLoading(true);
      try {
        let response: SearchResponse;
        
        if (filters.index === 'all') {
          response = await searchService.quickSearch(query);
        } else {
          const request: SearchRequest = {
            query,
            index: filters.index,
            page,
            page_size: 20,
            fuzzy: true,
          };

          // Add date filter
          if (filters.dateRange !== 'any') {
            const now = new Date();
            let startDate: Date;
            
            switch (filters.dateRange) {
              case 'day':
                startDate = new Date(now.setDate(now.getDate() - 1));
                break;
              case 'week':
                startDate = new Date(now.setDate(now.getDate() - 7));
                break;
              case 'month':
                startDate = new Date(now.setMonth(now.getMonth() - 1));
                break;
              case 'year':
                startDate = new Date(now.setFullYear(now.getFullYear() - 1));
                break;
            }

            request.filters = [
              {
                field: 'created_at',
                value: startDate.toISOString(),
                operator: 'gte',
              },
            ];
          }

          // Add sort
          if (filters.sortBy !== 'relevance') {
            request.sort = [
              {
                field: filters.sortBy === 'date' ? 'created_at' : 'name',
                order: 'desc',
              },
            ];
          }

          response = await searchService.search(request);
        }

        setResults(response);
      } catch (error) {
        console.error('Search error:', error);
        setResults(null);
      } finally {
        setIsLoading(false);
      }
    };

    performSearch();
  }, [query, filters, page]);

  // Update URL when search changes
  useEffect(() => {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (filters.index !== 'all') params.set('index', filters.index);
    if (page > 1) params.set('page', String(page));
    setSearchParams(params, { replace: true });
  }, [query, filters.index, page, setSearchParams]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  const getResultIcon = (source: Record<string, unknown>) => {
    if ('email' in source) return <User className="w-5 h-5" />;
    if ('content' in source) return <FileText className="w-5 h-5" />;
    if ('message' in source) return <MessageSquare className="w-5 h-5" />;
    return <FileText className="w-5 h-5" />;
  };

  const getResultType = (source: Record<string, unknown>): string => {
    if ('email' in source) return 'User';
    if ('content' in source) return 'Document';
    if ('message' in source) return 'Message';
    return 'Item';
  };

  const getResultTitle = (source: Record<string, unknown>): string => {
    if (source.first_name && source.last_name) {
      return `${source.first_name} ${source.last_name}`;
    }
    if (source.title) return String(source.title);
    if (source.name) return String(source.name);
    return 'Untitled';
  };

  const getResultDescription = (source: Record<string, unknown>): string => {
    if (source.email) return String(source.email);
    if (source.description) return String(source.description);
    if (source.content) return String(source.content).slice(0, 150) + '...';
    return '';
  };

  const handleResultClick = (hit: { id: string; source: Record<string, unknown> }) => {
    if ('email' in hit.source) {
      navigate(`/users/${hit.id}`);
    } else {
      navigate(`/documents/${hit.id}`);
    }
  };

  const indexTabs: { id: SearchIndex; label: string; icon: React.ReactNode }[] = [
    { id: 'all', label: 'All', icon: <Search className="w-4 h-4" /> },
    { id: 'users', label: 'Users', icon: <User className="w-4 h-4" /> },
    { id: 'documents', label: 'Documents', icon: <FileText className="w-4 h-4" /> },
    { id: 'messages', label: 'Messages', icon: <MessageSquare className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Search
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Find users, documents, and more
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
            className="input pl-10 w-full"
          />
        </div>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`btn-secondary flex items-center gap-2 ${showFilters ? 'bg-primary-50 text-primary-600' : ''}`}
        >
          <SlidersHorizontal className="w-4 h-4" />
          Filters
        </button>
        <button type="submit" className="btn-primary">
          Search
        </button>
      </form>

      {/* Index Tabs */}
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {indexTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setFilters({ ...filters, index: tab.id });
              setPage(1);
            }}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filters.index === tab.id
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.icon}
            {tab.label}
            {results && tab.id === filters.index && (
              <span className="px-1.5 py-0.5 text-xs bg-slate-100 dark:bg-slate-700 rounded">
                {results.total}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="card p-4 flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Date Range
            </label>
            <select
              value={filters.dateRange}
              onChange={(e) => setFilters({ ...filters, dateRange: e.target.value as FilterState['dateRange'] })}
              className="input"
            >
              <option value="any">Any time</option>
              <option value="day">Past 24 hours</option>
              <option value="week">Past week</option>
              <option value="month">Past month</option>
              <option value="year">Past year</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Sort by
            </label>
            <select
              value={filters.sortBy}
              onChange={(e) => setFilters({ ...filters, sortBy: e.target.value as FilterState['sortBy'] })}
              className="input"
            >
              <option value="relevance">Relevance</option>
              <option value="date">Date</option>
              <option value="name">Name</option>
            </select>
          </div>
          <button
            onClick={() => setFilters({ index: 'all', dateRange: 'any', sortBy: 'relevance' })}
            className="self-end text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1"
          >
            <X className="w-4 h-4" />
            Clear filters
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        </div>
      )}

      {/* Results */}
      {!isLoading && results && (
        <div className="space-y-4">
          {/* Results Summary */}
          <p className="text-sm text-slate-500">
            {results.total} results found in {results.took_ms.toFixed(0)}ms
          </p>

          {/* Results List */}
          {results.hits.length > 0 ? (
            <div className="space-y-3">
              {results.hits.map((hit) => (
                <div
                  key={hit.id}
                  onClick={() => handleResultClick({ id: hit.id, source: hit.source })}
                  className="card p-4 hover:border-primary-300 cursor-pointer transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center text-slate-500">
                      {getResultIcon(hit.source)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-medium text-slate-900 dark:text-white">
                          {getResultTitle(hit.source)}
                        </h3>
                        <span className="px-2 py-0.5 text-xs bg-slate-100 dark:bg-slate-700 rounded text-slate-500">
                          {getResultType(hit.source)}
                        </span>
                      </div>
                      <p className="text-slate-500 mt-1 line-clamp-2">
                        {getResultDescription(hit.source)}
                      </p>
                      {/* Highlights */}
                      {Object.keys(hit.highlights).length > 0 && (
                        <div className="mt-2 text-sm text-slate-600">
                          {Object.entries(hit.highlights).map(([field, fragments]) => (
                            <p key={field} className="italic">
                              ...{fragments[0]}...
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-slate-400">
                      <Calendar className="w-4 h-4 inline mr-1" />
                      {hit.source.created_at 
                        ? new Date(hit.source.created_at as string).toLocaleDateString()
                        : 'N/A'
                      }
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="card p-12 text-center">
              <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white">
                No results found
              </h3>
              <p className="text-slate-500 mt-1">
                Try different keywords or adjust your filters
              </p>
            </div>
          )}

          {/* Pagination */}
          {results.total_pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-500">
                Page {results.page} of {results.total_pages}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={!results.has_previous}
                  className="btn-secondary flex items-center gap-1 disabled:opacity-50"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={!results.has_next}
                  className="btn-secondary flex items-center gap-1 disabled:opacity-50"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !query && (
        <div className="card p-12 text-center">
          <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-900 dark:text-white">
            Start searching
          </h3>
          <p className="text-slate-500 mt-1">
            Enter a search term to find users, documents, and more
          </p>
        </div>
      )}
    </div>
  );
}
