import React, { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MessageSquare, Send, AlertCircle, Loader2 } from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import EmptyState from '../../components/common/EmptyState';
import { chatService } from '../../services/chatService';
import { authService } from '../../services/authService';
import { useNotificationSocket } from '../../hooks/useNotificationSocket';

function formatMessageTime(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const isToday =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear();

  if (isToday) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return date.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedConvId = searchParams.get('conversationId');

  const currentUser = authService.getCurrentUser();

  const [conversations, setConversations] = useState([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [activeConversationId, setActiveConversationId] = useState(
    requestedConvId ? parseInt(requestedConvId, 10) : null
  );

  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [hasOlder, setHasOlder] = useState(false);
  const [nextPage, setNextPage] = useState(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [messageError, setMessageError] = useState(null);
  const [inputBody, setInputBody] = useState('');
  const [isSending, setIsSending] = useState(false);

  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const scrollOffsetRef = useRef(null);
  const activeConversationIdRef = useRef(activeConversationId);
  activeConversationIdRef.current = activeConversationId;

  const scrollToBottom = (smooth = true) => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
    }
  };

  useLayoutEffect(() => {
    if (scrollOffsetRef.current !== null && messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop =
        messagesContainerRef.current.scrollHeight - scrollOffsetRef.current;
      scrollOffsetRef.current = null;
    }
  }, [messages]);

  // Fetch conversation list
  const loadConversations = useCallback(async () => {
    try {
      const data = await chatService.getConversations();
      const list = data.results || (Array.isArray(data) ? data : []);
      setConversations(list);

      // Auto-select conversation
      if (list.length > 0) {
        if (requestedConvId) {
          const matchId = parseInt(requestedConvId, 10);
          if (list.some((c) => c.id === matchId)) {
            setActiveConversationId(matchId);
          } else {
            setActiveConversationId(list[0].id);
          }
        } else if (!activeConversationIdRef.current) {
          setActiveConversationId(list[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setLoadingConversations(false);
    }
  }, [requestedConvId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load messages and mark conversation as read
  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      setHasOlder(false);
      setNextPage(null);
      return;
    }

    let isCancelled = false;

    const loadMessagesAndMarkRead = async () => {
      setLoadingMessages(true);
      setMessageError(null);
      setHasOlder(false);
      setNextPage(null);
      try {
        const data = await chatService.getMessages(activeConversationId, 1, 'desc');
        if (isCancelled) return;
        const list = (data.results || (Array.isArray(data) ? data : [])).slice().reverse();
        setMessages(list);
        setHasOlder(Boolean(data.next));
        setNextPage(data.next ? 2 : null);

        // Mark as read on backend
        await chatService.markAsRead(activeConversationId);

        // Update local unread count in conversations list
        setConversations((prev) =>
          prev.map((c) => (c.id === activeConversationId ? { ...c, unread_count: 0 } : c))
        );

        // Notify global unread listeners
        window.dispatchEvent(new CustomEvent('chat:unread-updated'));

        setTimeout(() => scrollToBottom(false), 50);
      } catch (err) {
        if (!isCancelled) {
          console.error('Failed to load messages:', err);
          setMessageError('Failed to load messages for this conversation.');
        }
      } finally {
        if (!isCancelled) {
          setLoadingMessages(false);
        }
      }
    };

    loadMessagesAndMarkRead();

    return () => {
      isCancelled = true;
    };
  }, [activeConversationId]);

  const handleLoadOlderMessages = async () => {
    if (!activeConversationId || !nextPage || loadingOlder) return;
    setLoadingOlder(true);
    try {
      const container = messagesContainerRef.current;
      if (container) {
        scrollOffsetRef.current = container.scrollHeight - container.scrollTop;
      }
      const data = await chatService.getMessages(activeConversationId, nextPage, 'desc');
      const olderChronological = (data.results || (Array.isArray(data) ? data : [])).slice().reverse();

      setMessages((prev) => {
        const existingIds = new Set(prev.map((m) => m.id));
        const uniqueOlder = olderChronological.filter((m) => !existingIds.has(m.id));
        return [...uniqueOlder, ...prev];
      });

      setHasOlder(Boolean(data.next));
      setNextPage(data.next ? nextPage + 1 : null);
    } catch (err) {
      console.error('Failed to load older messages:', err);
      setMessageError('Failed to load older messages.');
    } finally {
      setLoadingOlder(false);
    }
  };

  // Real-time chat message push handler
  const handleIncomingChatMessage = useCallback(
    async (newMsg) => {
      if (!newMsg || !newMsg.conversation_id) return;

      const belongsToActive = activeConversationIdRef.current === newMsg.conversation_id;

      if (belongsToActive) {
        // Append message if not duplicate
        setMessages((prev) => {
          if (prev.some((m) => m.id === newMsg.id)) {
            return prev;
          }
          return [...prev, newMsg];
        });

        setTimeout(() => scrollToBottom(true), 50);

        // Mark read immediately since user is actively viewing this conversation
        try {
          await chatService.markAsRead(newMsg.conversation_id);
          window.dispatchEvent(new CustomEvent('chat:unread-updated'));
        } catch {
          // Ignore read mark failure
        }
      }

      // Update conversation preview and unread count in sidebar list
      setConversations((prev) => {
        const exists = prev.some((c) => c.id === newMsg.conversation_id);
        if (!exists) {
          // If a new conversation was created elsewhere, reload list
          loadConversations();
          return prev;
        }

        return prev
          .map((c) => {
            if (c.id === newMsg.conversation_id) {
              return {
                ...c,
                last_message_preview: newMsg.body,
                last_message_at: newMsg.created_at,
                unread_count: belongsToActive ? 0 : (c.unread_count || 0) + 1,
              };
            }
            return c;
          })
          .sort((a, b) => new Date(b.last_message_at) - new Date(a.last_message_at));
      });
    },
    [loadConversations]
  );

  // Hook into WebSocket
  useNotificationSocket(null, handleIncomingChatMessage);

  // Send message handler
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const cleanBody = inputBody.trim();
    if (!cleanBody || !activeConversationId || isSending) return;

    if (cleanBody.length > 2000) {
      setMessageError('Message cannot exceed 2000 characters.');
      return;
    }

    setIsSending(true);
    setMessageError(null);

    try {
      const createdMessage = await chatService.sendMessage(activeConversationId, cleanBody);

      // Append my message
      setMessages((prev) => {
        if (prev.some((m) => m.id === createdMessage.id)) {
          return prev;
        }
        return [...prev, createdMessage];
      });

      // Update preview in list
      setConversations((prev) =>
        prev
          .map((c) =>
            c.id === activeConversationId
              ? {
                  ...c,
                  last_message_preview: createdMessage.body,
                  last_message_at: createdMessage.created_at,
                }
              : c
          )
          .sort((a, b) => new Date(b.last_message_at) - new Date(a.last_message_at))
      );

      setInputBody('');
      setTimeout(() => scrollToBottom(true), 50);
    } catch (err) {
      console.error('Failed to send message:', err);
      const detail = err.response?.data?.detail || err.response?.data?.body?.[0] || 'Failed to send message.';
      setMessageError(detail);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const activeConv = conversations.find((c) => c.id === activeConversationId);

  return (
    <DashboardLayout activeTab="chat">
      <div className="max-w-6xl mx-auto h-[calc(100vh-8rem)] min-h-[500px] flex flex-col bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="flex flex-1 min-h-0 divide-x divide-slate-200">
          {/* LEFT: Conversation List */}
          <aside className="w-full sm:w-80 md:w-96 flex flex-col min-h-0 bg-slate-50/50">
            <div className="p-4 border-b border-slate-200 bg-white">
              <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-indigo-600" />
                Messages
              </h1>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
              {loadingConversations ? (
                <div className="flex items-center justify-center py-12 text-slate-500">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                  <span className="ml-2 text-sm">Loading conversations...</span>
                </div>
              ) : conversations.length === 0 ? (
                <div className="p-6">
                  <EmptyState
                    icon={MessageSquare}
                    title="No conversations yet"
                    subtitle="Conversations are created when you message an applicant or opportunity poster."
                    className="py-6 px-2 bg-transparent border-0 shadow-none"
                  />
                </div>
              ) : (
                conversations.map((conv) => {
                  const isActive = conv.id === activeConversationId;
                  const otherName = conv.other_participant?.full_name || 'Participant';
                  const oppTitle = conv.opportunity?.title || 'Opportunity';
                  const initial = otherName.charAt(0).toUpperCase();

                  return (
                    <button
                      key={conv.id}
                      type="button"
                      onClick={() => {
                        setActiveConversationId(conv.id);
                        setSearchParams({ conversationId: conv.id });
                      }}
                      className={`w-full text-left p-4 transition-colors flex items-start gap-3 hover:bg-slate-100/70 ${
                        isActive ? 'bg-indigo-50/80 hover:bg-indigo-50' : 'bg-transparent'
                      }`}
                    >
                      <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center shrink-0 text-sm">
                        {initial}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <span className={`text-sm truncate ${isActive ? 'font-bold text-indigo-950' : 'font-semibold text-slate-900'}`}>
                            {otherName}
                          </span>
                          {conv.last_message_at && (
                            <span className="text-[11px] text-slate-400 shrink-0">
                              {formatMessageTime(conv.last_message_at)}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-indigo-600 font-medium truncate mt-0.5">
                          {oppTitle}
                        </p>
                        <div className="flex items-center justify-between gap-2 mt-1">
                          <p className="text-xs text-slate-500 truncate flex-1">
                            {conv.last_message_preview || 'No messages yet'}
                          </p>
                          {conv.unread_count > 0 && (
                            <span className="shrink-0 inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold text-white bg-indigo-600 rounded-full">
                              {conv.unread_count > 99 ? '99+' : conv.unread_count}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </aside>

          {/* RIGHT: Chat Window */}
          <section className="flex-1 flex flex-col min-h-0 bg-white">
            {activeConv ? (
              <>
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-white shrink-0">
                  <div className="min-w-0">
                    <h2 className="text-base font-bold text-slate-900 truncate">
                      {activeConv.other_participant?.full_name || 'Participant'}
                    </h2>
                    {activeConv.opportunity?.title && (
                      <p className="text-xs text-indigo-600 font-medium truncate">
                        Regarding: {activeConv.opportunity.title}
                      </p>
                    )}
                  </div>
                </div>

                {/* Message History */}
                <div ref={messagesContainerRef} className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 space-y-4 bg-slate-50/30">
                  {hasOlder && !loadingMessages && (
                    <div className="flex justify-center pb-2">
                      <button
                        type="button"
                        onClick={handleLoadOlderMessages}
                        disabled={loadingOlder}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-full shadow-xs hover:bg-slate-50 hover:text-slate-900 disabled:opacity-50 transition-colors cursor-pointer"
                      >
                        {loadingOlder ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                            <span>Loading older messages...</span>
                          </>
                        ) : (
                          <span>Load older messages</span>
                        )}
                      </button>
                    </div>
                  )}

                  {loadingMessages ? (
                    <div className="flex items-center justify-center h-full text-slate-500">
                      <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                      <span className="ml-2 text-sm">Loading messages...</span>
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-center text-slate-500 text-sm">
                      <p>No messages yet. Send a message to start the conversation!</p>
                    </div>
                  ) : (
                    messages.map((msg) => {
                      const isMe = msg.sender?.id === currentUser?.id;
                      return (
                        <div
                          key={msg.id}
                          className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
                        >
                          <div
                            className={`max-w-[85%] sm:max-w-md px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
                              isMe
                                ? 'bg-indigo-600 text-white rounded-br-xs shadow-xs'
                                : 'bg-white text-slate-800 border border-slate-200 rounded-bl-xs shadow-xs'
                            }`}
                          >
                            {/* Plain text rendering only: no HTML interpretation */}
                            {msg.body}
                          </div>
                          <span className="text-[10px] text-slate-400 mt-1 px-1">
                            {formatMessageTime(msg.created_at)}
                          </span>
                        </div>
                      );
                    })
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Error Banner */}
                {messageError && (
                  <div className="px-4 py-2 bg-red-50 border-t border-red-100 flex items-center gap-2 text-xs text-red-700">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{messageError}</span>
                  </div>
                )}

                {/* Input Bar */}
                <form
                  onSubmit={handleSendMessage}
                  className="p-3 sm:p-4 border-t border-slate-200 bg-white flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={inputBody}
                    onChange={(e) => setInputBody(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message..."
                    maxLength={2000}
                    disabled={isSending}
                    className="flex-1 px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-colors placeholder:text-slate-400 text-slate-900"
                  />
                  <button
                    type="submit"
                    disabled={isSending || !inputBody.trim()}
                    className="p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0 flex items-center justify-center"
                    title="Send message"
                    aria-label="Send message"
                  >
                    {isSending ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </form>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center p-6">
                <EmptyState
                  icon={MessageSquare}
                  title="No conversation selected"
                  subtitle="Select a conversation from the list to view and send messages."
                  className="py-12 bg-transparent border-0 shadow-none"
                />
              </div>
            )}
          </section>
        </div>
      </div>
    </DashboardLayout>
  );
}
