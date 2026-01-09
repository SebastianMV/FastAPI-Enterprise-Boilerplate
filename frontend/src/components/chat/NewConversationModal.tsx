/**
 * New conversation modal component.
 * 
 * Allows users to create direct or group conversations.
 */

import { useState, useEffect } from 'react';
import { 
  X, 
  Search as SearchIcon, 
  User, 
  Users,
  Check,
  Loader2
} from 'lucide-react';
import api, { chatService, type Conversation } from '@/services/api';

interface UserResult {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

interface NewConversationModalProps {
  onClose: () => void;
  onCreate: (conversation: Conversation) => void;
}

/**
 * Modal for creating a new conversation.
 */
export default function NewConversationModal({ onClose, onCreate }: NewConversationModalProps) {
  const [mode, setMode] = useState<'direct' | 'group'>('direct');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<UserResult[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<UserResult[]>([]);
  const [groupName, setGroupName] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Search users
  useEffect(() => {
    const searchUsers = async () => {
      if (!searchQuery.trim()) {
        setSearchResults([]);
        return;
      }

      try {
        setIsSearching(true);
        const response = await api.get<{ items: UserResult[] }>('/users', {
          params: { search: searchQuery, limit: 10 },
        });
        setSearchResults(response.data.items || []);
      } catch (err) {
        console.error('Failed to search users:', err);
      } finally {
        setIsSearching(false);
      }
    };

    const timer = setTimeout(searchUsers, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Toggle user selection
  const toggleUser = (user: UserResult) => {
    if (mode === 'direct') {
      setSelectedUsers([user]);
    } else {
      const isSelected = selectedUsers.some((u) => u.id === user.id);
      if (isSelected) {
        setSelectedUsers(selectedUsers.filter((u) => u.id !== user.id));
      } else {
        setSelectedUsers([...selectedUsers, user]);
      }
    }
  };

  // Check if user is selected
  const isUserSelected = (userId: string) => {
    return selectedUsers.some((u) => u.id === userId);
  };

  // Create conversation
  const handleCreate = async () => {
    if (selectedUsers.length === 0) {
      setError('Please select at least one user');
      return;
    }

    if (mode === 'group' && !groupName.trim()) {
      setError('Please enter a group name');
      return;
    }

    try {
      setIsCreating(true);
      setError(null);

      let conversation: Conversation;
      if (mode === 'direct') {
        conversation = await chatService.createDirectConversation(selectedUsers[0].id);
      } else {
        conversation = await chatService.createGroupConversation(
          groupName,
          selectedUsers.map((u) => u.id)
        );
      }

      onCreate(conversation);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
    } finally {
      setIsCreating(false);
    }
  };

  // Get user display name
  const getUserName = (user: UserResult) => {
    if (user.first_name || user.last_name) {
      return `${user.first_name} ${user.last_name}`.trim();
    }
    return user.email;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="w-full max-w-md bg-white dark:bg-slate-800 rounded-xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            New Conversation
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Toggle */}
        <div className="flex p-4 gap-2 border-b border-slate-200 dark:border-slate-700">
          <button
            onClick={() => { setMode('direct'); setSelectedUsers([]); }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
              mode === 'direct'
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
            }`}
          >
            <User className="w-4 h-4" />
            Direct Message
          </button>
          <button
            onClick={() => { setMode('group'); setSelectedUsers([]); }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
              mode === 'group'
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
            }`}
          >
            <Users className="w-4 h-4" />
            Group Chat
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Group name input (only for groups) */}
          {mode === 'group' && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Group Name
              </label>
              <input
                type="text"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="Enter group name..."
                className="input"
              />
            </div>
          )}

          {/* User search */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {mode === 'direct' ? 'Select User' : 'Add Participants'}
            </label>
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name or email..."
                className="w-full pl-9 pr-4 py-2 text-sm bg-slate-100 dark:bg-slate-700 border-0 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
              {isSearching && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 animate-spin" />
              )}
            </div>
          </div>

          {/* Selected users (for group) */}
          {mode === 'group' && selectedUsers.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {selectedUsers.map((user) => (
                <span
                  key={user.id}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full"
                >
                  {getUserName(user)}
                  <button
                    onClick={() => toggleUser(user)}
                    className="hover:text-primary-900"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Search results */}
          <div className="max-h-48 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg">
            {searchResults.length === 0 ? (
              <div className="p-4 text-center text-sm text-slate-500 dark:text-slate-400">
                {searchQuery ? 'No users found' : 'Start typing to search users'}
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-700">
                {searchResults.map((user) => (
                  <button
                    key={user.id}
                    onClick={() => toggleUser(user)}
                    className={`w-full flex items-center justify-between p-3 text-left transition-colors ${
                      isUserSelected(user.id)
                        ? 'bg-primary-50 dark:bg-primary-900/20'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center">
                        <User className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-slate-900 dark:text-white">
                          {getUserName(user)}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {user.email}
                        </p>
                      </div>
                    </div>
                    {isUserSelected(user.id) && (
                      <Check className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={onClose}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={selectedUsers.length === 0 || isCreating}
            className="btn-primary"
          >
            {isCreating ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              'Create'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
