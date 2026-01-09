/**
 * Chat window component.
 * 
 * Contains message list, input, and header for a conversation.
 */

import { useEffect, useRef, useState } from 'react';
import { 
  ArrowLeft, 
  Phone, 
  Video, 
  MoreVertical,
  Send,
  Paperclip,
  Smile,
  Image as ImageIcon,
  Check,
  CheckCheck,
  Loader2,
  User,
  Users
} from 'lucide-react';
import { useChat, type ChatMessage, type Conversation } from '@/hooks/useChat';
import { useAuthStore } from '@/stores/authStore';

interface ChatWindowProps {
  conversation: Conversation;
  onBack: () => void;
}

/**
 * Format message timestamp.
 */
function formatMessageTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
}

/**
 * Format date separator.
 */
function formatDateSeparator(timestamp: string): string {
  const date = new Date(timestamp);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  
  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  } else if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  } else {
    return date.toLocaleDateString([], { 
      weekday: 'long',
      month: 'long', 
      day: 'numeric' 
    });
  }
}

/**
 * Get message status icon.
 */
function MessageStatus({ status }: { status: ChatMessage['status'] }) {
  switch (status) {
    case 'read':
      return <CheckCheck className="w-4 h-4 text-blue-500" />;
    case 'delivered':
      return <CheckCheck className="w-4 h-4 text-slate-400" />;
    case 'sent':
      return <Check className="w-4 h-4 text-slate-400" />;
    case 'pending':
      return <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />;
    default:
      return null;
  }
}

/**
 * Chat window with messages and input.
 */
export default function ChatWindow({ conversation, onBack }: ChatWindowProps) {
  const { user } = useAuthStore();
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  const {
    messages,
    isLoading,
    isConnected,
    typingUsers,
    sendMessage,
    setTyping,
    hasMore,
    loadMore,
  } = useChat(conversation.id);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle send message
  const handleSend = async () => {
    if (!inputValue.trim() || isSending) return;
    
    const content = inputValue.trim();
    setInputValue('');
    setIsSending(true);
    
    try {
      await sendMessage(content);
    } catch (error) {
      console.error('Failed to send message:', error);
      setInputValue(content); // Restore input on error
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };

  // Handle key press
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Handle typing indicator
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    setTyping(e.target.value.length > 0);
  };

  // Get conversation display info
  const isGroup = conversation.type === 'group';
  const displayName = conversation.name || 
    conversation.participants.map(p => p.nickname || 'User').join(', ');
  const participantCount = conversation.participants.length;

  // Group messages by date
  const messagesByDate = messages.reduce<Record<string, ChatMessage[]>>((acc, msg) => {
    const date = new Date(msg.created_at).toDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(msg);
    return acc;
  }, {});

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="md:hidden p-1 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
            isGroup 
              ? 'bg-purple-100 dark:bg-purple-900/30' 
              : 'bg-primary-100 dark:bg-primary-900/30'
          }`}>
            {isGroup ? (
              <Users className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            ) : (
              <User className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            )}
          </div>
          
          <div>
            <h3 className="text-sm font-medium text-slate-900 dark:text-white">
              {displayName}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {typingUsers.length > 0 ? (
                <span className="text-primary-600 dark:text-primary-400">
                  {typingUsers.length === 1 ? 'Typing...' : `${typingUsers.length} people typing...`}
                </span>
              ) : isGroup ? (
                `${participantCount} members`
              ) : (
                isConnected ? 'Online' : 'Offline'
              )}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          <button className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
            <Phone className="w-5 h-5" />
          </button>
          <button className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
            <Video className="w-5 h-5" />
          </button>
          <button className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
            <MoreVertical className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Load more button */}
        {hasMore && (
          <button
            onClick={loadMore}
            disabled={isLoading}
            className="w-full text-center text-sm text-primary-600 dark:text-primary-400 py-2 hover:underline disabled:opacity-50"
          >
            {isLoading ? 'Loading...' : 'Load earlier messages'}
          </button>
        )}

        {/* Messages grouped by date */}
        {Object.entries(messagesByDate).map(([date, dateMessages]) => (
          <div key={date}>
            {/* Date separator */}
            <div className="flex items-center justify-center my-4">
              <span className="px-3 py-1 text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 rounded-full">
                {formatDateSeparator(dateMessages[0].created_at)}
              </span>
            </div>
            
            {/* Messages */}
            {dateMessages.map((message, index) => {
              const isOwn = message.sender_id === user?.id;
              const showAvatar = !isOwn && (
                index === 0 || 
                dateMessages[index - 1].sender_id !== message.sender_id
              );
              
              return (
                <div
                  key={message.id}
                  className={`flex items-end gap-2 mb-2 ${isOwn ? 'justify-end' : 'justify-start'}`}
                >
                  {/* Avatar for others */}
                  {!isOwn && (
                    <div className={`w-8 h-8 ${showAvatar ? 'visible' : 'invisible'}`}>
                      <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center">
                        <User className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                      </div>
                    </div>
                  )}
                  
                  {/* Message bubble */}
                  <div
                    className={`max-w-[70%] px-4 py-2 rounded-2xl ${
                      isOwn
                        ? 'bg-primary-600 text-white rounded-br-md'
                        : 'bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-bl-md'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap break-words">
                      {message.content}
                    </p>
                    <div className={`flex items-center justify-end gap-1 mt-1 ${
                      isOwn ? 'text-primary-200' : 'text-slate-400'
                    }`}>
                      <span className="text-[10px]">
                        {formatMessageTime(message.created_at)}
                      </span>
                      {isOwn && <MessageStatus status={message.status} />}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ))}
        
        {/* Empty state */}
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              No messages yet. Start the conversation!
            </p>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-700">
        <div className="flex items-end gap-2">
          <button className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
            <Paperclip className="w-5 h-5" />
          </button>
          <button className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
            <ImageIcon className="w-5 h-5" />
          </button>
          
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              rows={1}
              className="w-full px-4 py-2 pr-10 text-sm bg-slate-100 dark:bg-slate-700 border-0 rounded-2xl resize-none focus:ring-2 focus:ring-primary-500 max-h-32"
              style={{ minHeight: '40px' }}
            />
            <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600">
              <Smile className="w-5 h-5" />
            </button>
          </div>
          
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isSending}
            className="p-2.5 bg-primary-600 text-white rounded-full hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
