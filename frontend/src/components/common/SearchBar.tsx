import { useDebounce } from "@/hooks/useDebounce";
import { searchService, type SearchHit } from "@/services/api";
import { maskEmail, sanitizeSearchQuery, sanitizeText } from "@/utils/security";
import {
  Clock,
  FileText,
  Loader2,
  MessageSquare,
  Search,
  User,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

interface SearchBarProps {
  placeholder?: string;
  className?: string;
}

/**
 * Global search bar with autocomplete suggestions.
 *
 * Features:
 * - Debounced search input
 * - Quick search results dropdown
 * - Keyboard navigation
 * - Recent searches
 */
export default function SearchBar({
  placeholder,
  className = "",
}: SearchBarProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const effectivePlaceholder = placeholder || t("common.search");

  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<SearchHit[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  const debouncedQuery = useDebounce(query, 300);

  // Load recent searches from sessionStorage (not localStorage — search queries may contain PII)
  useEffect(() => {
    const saved = sessionStorage.getItem("recent-searches");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Validate schema: must be an array of strings, max 10 items
        if (Array.isArray(parsed)) {
          setRecentSearches(
            parsed
              .filter((s): s is string => typeof s === "string")
              .slice(0, 10),
          );
        }
      } catch {
        sessionStorage.removeItem("recent-searches");
      }
    }
  }, []);

  // Save recent search
  const saveRecentSearch = useCallback(
    (search: string) => {
      const updated = [
        search,
        ...recentSearches.filter((s) => s !== search),
      ].slice(0, 5);
      setRecentSearches(updated);
      sessionStorage.setItem("recent-searches", JSON.stringify(updated));
    },
    [recentSearches],
  );

  // Perform search when query changes
  useEffect(() => {
    const controller = new AbortController();

    const performSearch = async () => {
      if (!debouncedQuery || debouncedQuery.length < 2) {
        setResults([]);
        setSuggestions([]);
        return;
      }

      // Sanitize query to prevent search-engine injection
      const sanitized = sanitizeSearchQuery(debouncedQuery);
      if (!sanitized) {
        setResults([]);
        setSuggestions([]);
        return;
      }

      setIsLoading(true);
      try {
        const response = await searchService.quickSearch(
          sanitized,
          controller.signal,
        );
        if (!controller.signal.aborted) {
          setResults(response.hits.slice(0, 5));
          setSuggestions(response.suggestions || []);
        }
      } catch {
        // Search failed — don't log error details in production
        if (!controller.signal.aborted) {
          setResults([]);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    performSearch();

    return () => controller.abort();
  }, [debouncedQuery]);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        event.target instanceof Node &&
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target) &&
        !inputRef.current?.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const totalItems = results.length + suggestions.length;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % totalItems);
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + totalItems) % totalItems);
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < results.length) {
          handleResultClick(results[selectedIndex]);
        } else if (query) {
          handleSearch(query);
        }
        break;
      case "Escape":
        setIsOpen(false);
        inputRef.current?.blur();
        break;
    }
  };

  const handleSearch = useCallback(
    (searchQuery: string) => {
      if (!searchQuery.trim()) return;
      saveRecentSearch(searchQuery);
      setIsOpen(false);
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
    },
    [saveRecentSearch, navigate],
  );

  const handleResultClick = useCallback(
    (result: SearchHit) => {
      setIsOpen(false);
      // Navigate based on result type
      const source = result.source as Record<string, unknown>;
      if ("email" in source) {
        navigate(`/users/${encodeURIComponent(result.id)}`);
      } else {
        navigate(`/documents/${encodeURIComponent(result.id)}`);
      }
    },
    [navigate],
  );

  const getResultIcon = (result: SearchHit) => {
    const source = result.source as Record<string, unknown> | undefined;
    if (!source) return <FileText className="w-4 h-4" />;
    if ("email" in source) return <User className="w-4 h-4" />;
    if ("content" in source) return <FileText className="w-4 h-4" />;
    if ("message" in source) return <MessageSquare className="w-4 h-4" />;
    return <FileText className="w-4 h-4" />;
  };

  const getResultTitle = (result: SearchHit): string => {
    const source = result.source as Record<string, unknown> | undefined;
    if (!source) return t("common.untitled");
    if (source.first_name && source.last_name) {
      return sanitizeText(`${source.first_name} ${source.last_name}`);
    }
    if (source.title) return sanitizeText(String(source.title));
    if (source.name) return sanitizeText(String(source.name));
    return t("common.untitled");
  };

  const getResultSubtitle = (result: SearchHit): string => {
    const source = result.source as Record<string, unknown> | undefined;
    if (!source) return "";
    // Mask emails for privacy (defense-in-depth against PII exposure)
    if (source.email) return maskEmail(String(source.email));
    if (source.description)
      return sanitizeText(String(source.description).slice(0, 50));
    return "";
  };

  return (
    <div
      className={`relative ${className}`}
      role="combobox"
      aria-expanded={isOpen}
      aria-controls="search-listbox"
      aria-haspopup="listbox"
      aria-owns="search-listbox"
    >
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
            setSelectedIndex(-1);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={effectivePlaceholder}
          maxLength={500}
          autoComplete="off"
          role="searchbox"
          aria-autocomplete="list"
          aria-controls="search-listbox"
          aria-activedescendant={
            selectedIndex >= 0 ? `search-option-${selectedIndex}` : undefined
          }
          className="w-full pl-10 pr-10 py-2 bg-slate-100 dark:bg-slate-700 border-0 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setResults([]);
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 animate-spin" />
        )}
      </div>

      {/* Dropdown */}
      {isOpen && (query || recentSearches.length > 0) && (
        <div
          ref={dropdownRef}
          id="search-listbox"
          role="listbox"
          className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden z-50"
        >
          {/* Results */}
          {results.length > 0 && (
            <div className="p-2">
              <p className="px-2 py-1 text-xs font-medium text-slate-500 uppercase">
                {t("search.results")}
              </p>
              {results.map((result, index) => (
                <button
                  key={result.id}
                  id={`search-option-${index}`}
                  role="option"
                  aria-selected={selectedIndex === index}
                  onClick={() => handleResultClick(result)}
                  className={`w-full flex items-center gap-3 px-2 py-2 rounded-md text-left transition-colors ${
                    selectedIndex === index
                      ? "bg-primary-50 dark:bg-primary-900/20"
                      : "hover:bg-slate-50 dark:hover:bg-slate-700"
                  }`}
                >
                  <div className="flex-shrink-0 w-8 h-8 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center text-slate-500">
                    {getResultIcon(result)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                      {getResultTitle(result)}
                    </p>
                    <p className="text-xs text-slate-500 truncate">
                      {getResultSubtitle(result)}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Suggestions */}
          {suggestions.length > 0 && (
            <div className="p-2 border-t border-slate-100 dark:border-slate-700">
              <p className="px-2 py-1 text-xs font-medium text-slate-500 uppercase">
                {t("search.suggestions")}
              </p>
              {suggestions.map((suggestion, index) => (
                <button
                  key={suggestion}
                  onClick={() => handleSearch(suggestion)}
                  className={`w-full flex items-center gap-2 px-2 py-2 rounded-md text-left transition-colors ${
                    selectedIndex === results.length + index
                      ? "bg-primary-50 dark:bg-primary-900/20"
                      : "hover:bg-slate-50 dark:hover:bg-slate-700"
                  }`}
                >
                  <Search className="w-4 h-4 text-slate-400" />
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {suggestion}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Recent Searches */}
          {!query && recentSearches.length > 0 && (
            <div className="p-2">
              <p className="px-2 py-1 text-xs font-medium text-slate-500 uppercase">
                {t("search.recentSearches")}
              </p>
              {recentSearches.map((search) => (
                <button
                  key={search}
                  onClick={() => handleSearch(search)}
                  className="w-full flex items-center gap-2 px-2 py-2 rounded-md text-left hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                >
                  <Clock className="w-4 h-4 text-slate-400" />
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {search}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* No Results */}
          {query &&
            !isLoading &&
            results.length === 0 &&
            suggestions.length === 0 && (
              <div className="p-4 text-center text-slate-500">
                <p className="text-sm">
                  {t("search.noResultsFor", { query: sanitizeText(query) })}
                </p>
              </div>
            )}

          {/* Search All */}
          {query && (
            <div className="p-2 border-t border-slate-100 dark:border-slate-700">
              <button
                onClick={() => handleSearch(query)}
                className="w-full px-2 py-2 text-sm text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-md transition-colors text-left"
              >
                {t("search.searchAll", { query: sanitizeText(query) })} →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
