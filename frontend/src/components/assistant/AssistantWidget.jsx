import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { X, Send, Sparkles, RefreshCw, Bot, User } from 'lucide-react';
import { authService } from '../../services/authService';
import { assistantService } from '../../services/assistantService';

/**
 * AssistantWidget - Floating AI Assistant chat panel for students.
 */
export default function AssistantWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);

  // Initial welcome message
  const [messages, setMessages] = useState([
    {
      id: 'welcome-msg',
      sender: 'assistant',
      isWelcome: true,
      text: "Hi! I'm your NextGig AI Assistant. I can help answer platform questions or suggest open opportunities matching your profile.",
      opportunities: [],
    },
  ]);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const isMountedRef = useRef(true);

  // Track component mount status to avoid post-unmount state updates
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Auto-scroll to newest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, loading, isOpen]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Close panel on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  /**
   * Constructs valid history to send to backend:
   * - Excludes welcome message and error notices
   * - Excludes failed user messages (only status === 'sent')
   * - Trims content to first 1000 characters
   * - Keeps at most the last 10 valid turns
   */
  const buildHistory = (currentMessages) => {
    const validHistory = [];
    for (const msg of currentMessages) {
      if (msg.isWelcome) continue;
      if (msg.sender === 'user' && msg.status === 'sent') {
        validHistory.push({
          role: 'user',
          content: (msg.text || '').substring(0, 1000),
        });
      } else if (msg.sender === 'assistant' && !msg.isWelcome) {
        validHistory.push({
          role: 'assistant',
          content: (msg.text || '').substring(0, 1000),
        });
      }
    }
    return validHistory.slice(-10);
  };

  /**
   * Handles sending a new message or retrying a failed message.
   * @param {string} textToSend - Text content to send
   * @param {string|null} retryMsgId - Message ID if retrying an existing failed message
   */
  const handleSend = async (textToSend = inputText, retryMsgId = null) => {
    const trimmed = textToSend.trim();
    if (!trimmed || loading) return;

    let userMsgId = retryMsgId;
    let historyPayload = [];

    if (retryMsgId) {
      // Retrying existing failed message: update status to 'sending' and clear error
      setMessages((prev) =>
        prev.map((m) =>
          m.id === retryMsgId ? { ...m, status: 'sending', errorText: null } : m
        )
      );
      historyPayload = buildHistory(messages.filter((m) => m.id !== retryMsgId));
    } else {
      // New message
      userMsgId = `user-${Date.now()}`;
      const newUserMsg = {
        id: userMsgId,
        sender: 'user',
        text: trimmed,
        status: 'sending',
        errorText: null,
      };
      const updatedMessages = [...messages, newUserMsg];
      setMessages(updatedMessages);
      setInputText('');
      historyPayload = buildHistory(messages);
    }

    setLoading(true);

    try {
      const response = await assistantService.sendMessage(trimmed, historyPayload);

      if (!isMountedRef.current) return;

      // Mark user message as sent
      setMessages((prev) =>
        prev.map((m) => (m.id === userMsgId ? { ...m, status: 'sent' } : m))
      );

      // Add assistant response
      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: response.reply || '',
        opportunities: response.opportunities || [],
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      if (!isMountedRef.current) return;

      // Determine error message based on error.status or detail
      let errorDisplay = 'Something went wrong. Please try again.';
      const status = err.status;

      if (status === 429) {
        errorDisplay = "You're sending messages too quickly. Please wait a moment.";
      } else if (status === 400) {
        errorDisplay = "Your message couldn't be sent. Try a shorter message.";
      } else if ((status === 502 || status === 503) && err.message) {
        errorDisplay = err.message;
      } else if (err.message) {
        errorDisplay = err.message;
      }

      // Keep user message visible with status 'error' and inline error string
      setMessages((prev) =>
        prev.map((m) =>
          m.id === userMsgId
            ? { ...m, status: 'error', errorText: errorDisplay }
            : m
        )
      );
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleExampleClick = (questionText) => {
    setInputText(questionText);
    handleSend(questionText);
  };

  // Render ONLY for students (evaluated after all hooks)
  const userRole = authService.getUserRole();
  if (userRole !== 'student') {
    return null;
  }

  return (
    <div className="assistant-widget-container">
      {/* Floating Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-3 rounded-full shadow-lg transition-all transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          aria-label="Open AI Assistant"
        >
          <Sparkles className="w-5 h-5" />
          <span className="text-sm font-semibold">AI Assistant</span>
        </button>
      )}

      {/* Floating Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-4 right-4 sm:right-6 z-50 w-[calc(100vw-2rem)] sm:w-96 h-[540px] max-h-[85vh] bg-white border border-slate-200 rounded-2xl shadow-xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white shrink-0">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-sm leading-tight">NextGig AI Assistant</h3>
                <p className="text-[11px] text-slate-300">Student Platform Guide</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              aria-label="Close assistant panel"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages Body */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-slate-50">
            {messages.map((msg) => {
              const isUser = msg.sender === 'user';
              return (
                <div key={msg.id} className="space-y-2">
                  <div className={`flex gap-2.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
                    {!isUser && (
                      <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div
                      className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 text-sm shadow-sm ${
                        isUser
                          ? 'bg-indigo-600 text-white rounded-br-none'
                          : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none'
                      }`}
                    >
                      <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                        {msg.text}
                      </div>

                      {/* Welcome Message Example Questions */}
                      {msg.isWelcome && (
                        <div className="mt-3 pt-2 border-t border-slate-100 space-y-1.5">
                          <p className="text-[11px] font-medium text-slate-500">Try asking:</p>
                          <button
                            onClick={() => handleExampleClick('How do I apply for an opportunity?')}
                            className="block w-full text-left text-xs text-indigo-600 hover:text-indigo-800 bg-indigo-50/70 hover:bg-indigo-50 px-2.5 py-1.5 rounded-lg transition-colors"
                          >
                            💡 How do I apply for an opportunity?
                          </button>
                          <button
                            onClick={() => handleExampleClick('What opportunities fit my skills?')}
                            className="block w-full text-left text-xs text-indigo-600 hover:text-indigo-800 bg-indigo-50/70 hover:bg-indigo-50 px-2.5 py-1.5 rounded-lg transition-colors"
                          >
                            💡 What opportunities fit my skills?
                          </button>
                        </div>
                      )}

                      {/* Opportunity Cards */}
                      {msg.opportunities && msg.opportunities.length > 0 && (
                        <div className="mt-3 space-y-2 pt-2 border-t border-slate-100">
                          <p className="text-[11px] font-semibold text-slate-600">Matching Opportunities:</p>
                          {msg.opportunities.map((opp) => (
                            <Link
                              key={opp.id}
                              to={`/opportunities/${opp.id}`}
                              className="block bg-slate-50 hover:bg-indigo-50/60 border border-slate-200 rounded-xl p-2.5 text-left transition-colors group"
                            >
                              <div className="flex items-center justify-between gap-1.5">
                                <h4 className="font-semibold text-xs text-slate-900 group-hover:text-indigo-600 truncate">
                                  {opp.title}
                                </h4>
                                {opp.category && (
                                  <span className="text-[10px] font-medium px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full shrink-0">
                                    {opp.category.replace('_', ' ')}
                                  </span>
                                )}
                              </div>

                              <div className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-slate-500">
                                {opp.city && <span>📍 {opp.city}</span>}
                                {opp.work_mode && <span className="capitalize">🏢 {opp.work_mode}</span>}
                                {opp.pay_type && <span className="uppercase font-medium">💰 {opp.pay_type}</span>}
                                {opp.deadline && (
                                  <span>
                                    📅 Due{' '}
                                    {new Date(opp.deadline).toLocaleDateString('en-US', {
                                      month: 'short',
                                      day: 'numeric',
                                    })}
                                  </span>
                                )}
                              </div>
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>

                    {isUser && (
                      <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5 text-xs font-semibold">
                        <User className="w-4 h-4" />
                      </div>
                    )}
                  </div>

                  {/* Inline Error Notice for Failed User Message */}
                  {msg.status === 'error' && (
                    <div className="flex items-center justify-end gap-2 pr-9 text-xs">
                      <span className="text-red-600">{msg.errorText || 'Failed to send.'}</span>
                      <button
                        onClick={() => handleSend(msg.text, msg.id)}
                        disabled={loading}
                        className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium underline cursor-pointer disabled:opacity-50"
                      >
                        <RefreshCw className="w-3 h-3" /> Retry
                      </button>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Typing Indicator */}
            {loading && (
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-none px-4 py-2.5 text-xs text-slate-500 shadow-sm flex items-center gap-1.5">
                  <span className="font-medium">Assistant is thinking</span>
                  <span className="inline-flex gap-0.5">
                    <span className="w-1 h-1 bg-indigo-600 rounded-full animate-bounce"></span>
                    <span className="w-1 h-1 bg-indigo-600 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                    <span className="w-1 h-1 bg-indigo-600 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Footer Input Area */}
          <div className="p-3 bg-white border-t border-slate-200 shrink-0 space-y-2">
            <div className="relative flex items-center">
              <textarea
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                maxLength={500}
                placeholder="Ask about opportunities or NextGig..."
                rows={2}
                className="w-full text-xs text-slate-800 bg-slate-50 border border-slate-200 rounded-xl p-2.5 pr-10 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white disabled:opacity-50"
              />
              <button
                onClick={() => handleSend()}
                disabled={loading || !inputText.trim()}
                className="absolute right-2 bottom-2.5 p-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
                aria-label="Send message"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center justify-between text-[10px] text-slate-400 px-1">
              <span>{inputText.length}/500</span>
              <span>Press Enter to send</span>
            </div>

            {/* Privacy & Honesty Notices */}
            <div className="text-[10px] text-slate-400 space-y-0.5 px-1 border-t border-slate-100 pt-1.5 leading-tight">
              <p>Your skills and city are shared with an AI service to give better answers.</p>
              <p>AI can make mistakes. Check details on the opportunity page.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
