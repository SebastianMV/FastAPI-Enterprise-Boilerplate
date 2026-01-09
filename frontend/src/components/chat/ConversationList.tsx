/**
 * Conversation list component.
 * 
 * Displays a list of conversations with preview, timestamp and unread count.
 */

import { User, Users } from 'lucide-react';
import type { Conversation } from '@/hooks/useChat';

/**
 * Format timestamp for conversation preview.
 */
function formatTime(timestamp?: string): string {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } else if (diffDays === 1) {
    return 'Yesterday';
  } else if (diffDays < 7) {
    return date.toLocaleDateString([], { weekday: 'short' });
  } else {
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }
}

interface ConversationListProps {
  conversations: Conversation[];
  selectedId?: string;
  onSelect: (id: string) => void;
}

/**
 * List of conversations.
 */
export default function ConversationList({ 
  conversations, 
  selectedId, 
  onSelect 
}: ConversationListProps) {
  return (
    <div className="divide-y divide-slate-100 dark:divide-slate-700/50">
      {conversations.map((conversation) => (
        <ConversationItem
          key={conversation.id}
          conversation={conversation}
          isSelected={conversation.id === selectedId}
          onSelect={() => onSelect(conversation.id)}
        />
      ))}
    </div>
  );
}

interface ConversationItemProps {
  conversation: Conversation;
  isSelected: boolean;
  onSelect: () => void;
}

/**
 * Single conversation item.
 */
function ConversationItem({ conversation, isSelected, onSelect }: ConversationItemProps) {
  const isGroup = conversation.type === 'group';
  
  // Get display name
  const displayName = conversation.name || 
    (conversation.participants.length > 0 
      ? conversation.participants.map(p => p.nickname || 'User').join(', ')
      : 'Unknown');

  return (
    <button
      onClick={onSelect}
      className={`w-full flex items-start gap-3 p-3 text-left transition-colors ${
        isSelected 
          ? 'bg-primary-50 dark:bg-primary-900/20' 
          : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'
      }`}
    >
      {/* Avatar */}
      <div className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center ${
        isGroup 
          ? 'bg-purple-100 dark:bg-purple-900/30' 
          : 'bg-primary-100 dark:bg-primary-900/30'
      }`}>
        {isGroup ? (
          <Users className="w-6 h-6 text-purple-600 dark:text-purple-400" />
        ) : (
          <User className="w-6 h-6 text-primary-600 dark:text-primary-400" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <h4 className={`text-sm font-medium truncate ${
            isSelected 
              ? 'text-primary-700 dark:text-primary-300' 
              : 'text-slate-900 dark:text-white'
          }`}>
            {displayName}
          </h4>
          {conversation.last_message_at && (
            <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
              {formatTime(conversation.last_message_at)}
            </span>
          )}
        </div>
        
        <div className="flex items-center justify-between gap-2 mt-0.5">
          <p className="text-sm text-slate-500 dark:text-slate-400 truncate">
            {conversation.last_message_preview || 'No messages yet'}
          </p>
          {conversation.unread_count > 0 && (
            <span className="flex-shrink-0 min-w-[20px] h-5 px-1.5 flex items-center justify-center text-xs font-medium text-white bg-primary-600 rounded-full">
              {conversation.unread_count > 99 ? '99+' : conversation.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
