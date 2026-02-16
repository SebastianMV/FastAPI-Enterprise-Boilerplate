import { useCallback, useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
  X,
  Shield,
  FileEdit
} from 'lucide-react';
import { searchService, type SearchResponse, type SearchRequest } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { sanitizeText, sanitizeSearchQuery, maskEmail } from '@/utils/security';

type SearchIndex = 'users' | 'documents' | 'messages' | 'posts' | 'audit_logs' | 'all';

interface FilterState {
  index: SearchIndex;
  dateRange: 'any' | 'day' | 'week' | 'month' | 'year';
  sortBy: 'relevance' | 'date' | 'name';
}

/**
 * Search results page with filters and pagination.
 */
export default function SearchPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);

  const initialQuery = searchParams.get('q') || '';
  const initialIndex = (searchParams.get('index') || 'all') as SearchIndex;
  const rawPage = parseInt(searchParams.get('page') || '1', 10);
  const initialPage = Math.max(1, Math.min(1000, isNaN(rawPage) ? 1 : rawPage));

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
    const abortController = new AbortController();
    
    const performSearch = async () => {
      if (!query) {
        setResults(null);
        return;
      }

      // Sanitize query to prevent search-engine operator injection
      const sanitized = sanitizeSearchQuery(query);
      if (!sanitized) {
        setResults(null);
        return;
      }

      setIsLoading(true);
      try {
        let response: SearchResponse;
        
        if (filters.index === 'all') {
          response = await searchService.quickSearch(sanitized, abortController.signal);
        } else {
          const request: SearchRequest = {
            query: sanitized,
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
                startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                break;
              case 'week':
                startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                break;
              case 'month': {
                const d = new Date(now);
                d.setMonth(d.getMonth() - 1);
                startDate = d;
                break;
              }
              case 'year': {
                const d = new Date(now);
                d.setFullYear(d.getFullYear() - 1);
                startDate = d;
                break;
              }
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

          response = await searchService.search(request, abortController.signal);
        }

        setResults(response);
      } catch {
        if (abortController.signal.aborted) return;
        // Search failed — don't log error details in production
        setResults(null);
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    performSearch();
    
    return () => {
      abortController.abort();
    };
  }, [query, filters, page]);

  // Update URL when search changes
  useEffect(() => {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (filters.index !== 'all') params.set('index', filters.index);
    if (page > 1) params.set('page', String(page));
    setSearchParams(params, { replace: true });
  }, [query, filters.index, page, setSearchParams]);

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  }, []);

  const getResultIcon = (source: Record<string, unknown>) => {
    if ('email' in source) return <User className="w-5 h-5" />;
    if ('action' in source && 'actor_id' in source) return <Shield className="w-5 h-5" />;
    if ('content' in source) return <FileText className="w-5 h-5" />;
    if ('message' in source) return <MessageSquare className="w-5 h-5" />;
    if ('body' in source || 'post' in source) return <FileEdit className="w-5 h-5" />;
    return <FileText className="w-5 h-5" />;
  };

  const getResultType = (source: Record<string, unknown>): string => {
    if ('email' in source) return t('search.resultTypes.user');
    if ('action' in source && 'actor_id' in source) return t('search.resultTypes.auditLog');
    if ('content' in source) return t('search.resultTypes.document');
    if ('message' in source) return t('search.resultTypes.message');
    if ('body' in source || 'post' in source) return t('search.resultTypes.post');
    return t('search.resultTypes.item');
  };

  const getResultTitle = (source: Record<string, unknown>): string => {
    if (source.first_name && source.last_name) {
      return sanitizeText(`${source.first_name} ${source.last_name}`);
    }
    if (source.action && source.resource_type) {
      return t('search.actionOnResource', { action: sanitizeText(String(source.action)), resource: sanitizeText(String(source.resource_type)) });
    }
    if (source.title) return sanitizeText(String(source.title));
    if (source.name) return sanitizeText(String(source.name));
    return t('search.untitled');
  };

  const getResultDescription = (source: Record<string, unknown>): string => {
    if (source.email) return maskEmail(String(source.email));
    if (source.actor_email) return t('search.byActor', { email: maskEmail(String(source.actor_email)) });
    if (source.description) return sanitizeText(String(source.description));
    if (source.content) return sanitizeText(String(source.content).slice(0, 150)) + '...';
    return '';
  };

  const handleResultClick = useCallback((hit: { id: string; source: Record<string, unknown> }) => {
    if ('email' in hit.source) {
      navigate(`/users/${encodeURIComponent(hit.id)}`);
    } else if ('action' in hit.source && 'actor_id' in hit.source) {
      // Audit log entry - could navigate to audit details if available
      navigate(`/security/audit?id=${encodeURIComponent(hit.id)}`);
    } else {
      navigate(`/documents/${encodeURIComponent(hit.id)}`);
    }
  }, [navigate]);

  const indexTabs: { id: SearchIndex; label: string; icon: React.ReactNode }[] = [
    { id: 'all', label: t('search.indexes.all'), icon: <Search className="w-4 h-4" /> },
    { id: 'users', label: t('search.indexes.users'), icon: <User className="w-4 h-4" /> },
    { id: 'documents', label: t('search.indexes.documents'), icon: <FileText className="w-4 h-4" /> },
    { id: 'messages', label: t('search.indexes.messages'), icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'posts', label: t('search.indexes.posts'), icon: <FileEdit className="w-4 h-4" /> },
    // Only show audit_logs tab to superusers
    ...(user?.is_superuser ? [{ id: 'audit_logs' as SearchIndex, label: t('search.indexes.auditLogs'), icon: <Shield className="w-4 h-4" /> }] : []),
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          {t('search.title')}
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          {t('search.subtitle')}
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
            placeholder={t('search.searchPlaceholder')}
            className="input pl-10 w-full"
            maxLength={500}
          />
        </div>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`btn-secondary flex items-center gap-2 ${showFilters ? 'bg-primary-50 text-primary-600' : ''}`}
        >
          <SlidersHorizontal className="w-4 h-4" />
          {t('search.filters')}
        </button>
        <button type="submit" className="btn-primary">
          {t('common.search')}
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
              {t('search.dateRange')}
            </label>
            <select
              value={filters.dateRange}
              onChange={(e) => setFilters({ ...filters, dateRange: e.target.value as FilterState['dateRange'] })}
              className="input"
            >
              <option value="any">{t('search.dateRangeOptions.any')}</option>
              <option value="day">{t('search.dateRangeOptions.day')}</option>
              <option value="week">{t('search.dateRangeOptions.week')}</option>
              <option value="month">{t('search.dateRangeOptions.month')}</option>
              <option value="year">{t('search.dateRangeOptions.year')}</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('search.sortBy')}
            </label>
            <select
              value={filters.sortBy}
              onChange={(e) => setFilters({ ...filters, sortBy: e.target.value as FilterState['sortBy'] })}
              className="input"
            >
              <option value="relevance">{t('search.sortByOptions.relevance')}</option>
              <option value="date">{t('search.sortByOptions.date')}</option>
              <option value="name">{t('search.sortByOptions.name')}</option>
            </select>
          </div>
          <button
            onClick={() => setFilters({ index: 'all', dateRange: 'any', sortBy: 'relevance' })}
            className="self-end text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1"
          >
            <X className="w-4 h-4" />
            {t('search.clearFilters')}
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
            {t('search.resultsFound', { count: results.total, ms: results.took_ms.toFixed(0) })}
          </p>

          {/* Results List */}
          {results.hits.length > 0 ? (
            <div className="space-y-3">
              {results.hits.map((hit) => (
                <div
                  key={hit.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleResultClick({ id: hit.id, source: hit.source })}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleResultClick({ id: hit.id, source: hit.source }); } }}
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
                      {/* Highlights — sanitize server-returned fragments */}
                      {Object.keys(hit.highlights).length > 0 && (
                        <div className="mt-2 text-sm text-slate-600">
                          {Object.entries(hit.highlights).map(([field, fragments]) => (
                            <p key={field} className="italic">
                              ...{sanitizeText(fragments[0])}...
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-slate-400">
                      <Calendar className="w-4 h-4 inline mr-1" />
                      {hit.source.created_at 
                        ? new Date(hit.source.created_at as string).toLocaleDateString()
                        : t('common.na')
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
                {t('search.noResults')}
              </h3>
              <p className="text-slate-500 mt-1">
                {t('search.tryDifferentKeywords')}
              </p>
            </div>
          )}

          {/* Pagination */}
          {results.total_pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-500">
                {t('search.page', { current: results.page, total: results.total_pages })}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={!results.has_previous}
                  className="btn-secondary flex items-center gap-1 disabled:opacity-50"
                >
                  <ChevronLeft className="w-4 h-4" />
                  {t('search.previous')}
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={!results.has_next}
                  className="btn-secondary flex items-center gap-1 disabled:opacity-50"
                >
                  {t('search.next')}
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
            {t('search.startSearching')}
          </h3>
          <p className="text-slate-500 mt-1">
            {t('search.enterSearchTerm')}
          </p>
        </div>
      )}
    </div>
  );
}
