/**
 * Chat page with conversation list and messaging interface.
 * 
 * Features:
 * - List of conversations (direct and group)
 * - Real-time messaging
 * - Typing indicators
 * - Message status (sent, delivered, read)
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  MessageSquare, 
  Plus, 
  Search as SearchIcon,
  Loader2
} from 'lucide-react';
import { chatService, type Conversation } from '@/services/api';
import ConversationList from '@/components/chat/ConversationList';
import ChatWindow from '@/components/chat/ChatWindow';
import NewConversationModal from '@/components/chat/NewConversationModal';


/**
 * Main Chat page component.
 */
export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId?: string }>();
  const navigate = useNavigate();
  
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [isMobileListVisible, setIsMobileListVisible] = useState(!conversationId);

  // Fetch conversations on mount
  useEffect(() => {
    fetchConversations();
  }, []);

  // Update mobile view when conversation changes
  useEffect(() => {
    setIsMobileListVisible(!conversationId);
  }, [conversationId]);

  const fetchConversations = async () => {
    try {
      setIsLoading(true);
      const conversations = await chatService.getConversations();
      setConversations(conversations);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectConversation = (id: string) => {
    navigate(`/chat/${id}`);
    setIsMobileListVisible(false);
  };

  const handleBackToList = () => {
    navigate('/chat');
    setIsMobileListVisible(true);
  };

  const handleNewConversation = async (conversation: Conversation) => {
    setConversations([conversation, ...conversations]);
    navigate(`/chat/${conversation.id}`);
    setShowNewModal(false);
  };

  // Filter conversations by search
  const filteredConversations = conversations.filter((conv) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      conv.name?.toLowerCase().includes(query) ||
      conv.last_message_preview?.toLowerCase().includes(query) ||
      conv.participants.some((p) => p.nickname?.toLowerCase().includes(query))
    );
  });

  // Get selected conversation
  const selectedConversation = conversations.find((c) => c.id === conversationId);

  return (
    <div className="h-[calc(100vh-7rem)] flex bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Conversations Sidebar */}
      <div 
        className={`w-full md:w-80 lg:w-96 border-r border-slate-200 dark:border-slate-700 flex flex-col ${
          isMobileListVisible ? 'block' : 'hidden md:flex'
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Messages
            </h2>
            <button
              onClick={() => setShowNewModal(true)}
              className="p-2 text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
              title="New conversation"
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>
          
          {/* Search */}
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-slate-100 dark:bg-slate-700 border-0 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-primary-600 animate-spin" />
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
              <MessageSquare className="w-12 h-12 text-slate-300 dark:text-slate-600 mb-3" />
              <h3 className="text-sm font-medium text-slate-900 dark:text-white">
                {searchQuery ? 'No conversations found' : 'No conversations yet'}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {searchQuery ? 'Try a different search' : 'Start a new conversation'}
              </p>
              {!searchQuery && (
                <button
                  onClick={() => setShowNewModal(true)}
                  className="mt-4 btn-primary text-sm"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  New Conversation
                </button>
              )}
            </div>
          ) : (
            <ConversationList
              conversations={filteredConversations}
              selectedId={conversationId}
              onSelect={handleSelectConversation}
            />
          )}
        </div>
      </div>

      {/* Chat Window */}
      <div 
        className={`flex-1 flex flex-col ${
          !isMobileListVisible ? 'block' : 'hidden md:flex'
        }`}
      >
        {conversationId && selectedConversation ? (
          <ChatWindow
            conversation={selectedConversation}
            onBack={handleBackToList}
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
            <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mb-4">
              <MessageSquare className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-medium text-slate-900 dark:text-white">
              Select a conversation
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
              Choose a conversation from the list or start a new one to begin messaging.
            </p>
            <button
              onClick={() => setShowNewModal(true)}
              className="mt-6 btn-primary"
            >
              <Plus className="w-4 h-4 mr-2" />
              Start New Conversation
            </button>
          </div>
        )}
      </div>

      {/* New Conversation Modal */}
      {showNewModal && (
        <NewConversationModal
          onClose={() => setShowNewModal(false)}
          onCreate={handleNewConversation}
        />
      )}
    </div>
  );
}
