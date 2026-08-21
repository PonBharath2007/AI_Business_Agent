import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Bot,
  User,
  Trash2,
  ArrowRight,
  TrendingUp,
  AlertCircle,
  FileText,
  CheckCircle2,
  CornerDownLeft
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';

const SUGGESTED_PROMPTS = [
  "What needs my attention today?",
  "Show all overdue invoices.",
  "Which customers have pending payments?",
  "Prepare payment reminders for all overdue customers.",
  "Why are payments getting delayed?",
  "What are my highest priority tasks?",
  "Which customers are repeatedly paying late?",
  "Summarize this week's business activities."
];

const CommandCenterPage = ({ onNavigate }) => {
  const { business } = useBusiness();
  const { addToast } = useNotifications();

  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'ai',
      text: `👋 Hello! I am your **AI Business Operations Agent** for **${business?.name || 'Summit Digital Agency'}**.\n\nI monitor your invoices, track customer communications, extract document data, and manage pending approvals.\n\nHow can I assist your operations today?`,
      suggested_actions: [
        { label: "What needs my attention today?", action: "prompt", target: "What needs my attention today?" },
        { label: "Show unpaid invoices", action: "prompt", target: "Show all unpaid invoices." },
        { label: "Check Overdue Payments", action: "prompt", target: "Which customers have overdue payments?" }
      ],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (textToSend) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || loading) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      // Send to FastAPI AI route
      const historyPayload = messages.map((m) => ({
        role: m.sender === 'user' ? 'user' : 'model',
        text: m.text
      }));

      const res = await api.post('/ai/chat', {
        message: query,
        conversation_history: historyPayload
      });

      const aiMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: res.data.response,
        suggested_actions: res.data.suggested_actions || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      console.error('AI chat error:', err);
      const errorMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: "⚠️ I encountered an issue retrieving that information. Please try asking again or check your backend connection.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleActionClick = (action) => {
    if (action.action === 'prompt') {
      handleSendMessage(action.target);
    } else if (action.action === 'navigate') {
      const tab = action.target.replace('/', '');
      onNavigate(tab || 'dashboard');
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: Date.now(),
        sender: 'ai',
        text: `Conversation cleared. Ready for your next query!`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] glass-panel rounded-2xl border border-slate-800 overflow-hidden bg-slate-950/60">
      {/* Chat Header */}
      <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">AI Command Center</h3>
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Natural language database operations & reasoning</p>
          </div>
        </div>

        <Button
          onClick={clearChat}
          variant="ghost"
          size="sm"
          icon={Trash2}
          className="text-xs text-slate-400 hover:text-rose-400"
        >
          Clear Chat
        </Button>
      </div>

      {/* Suggested Prompts Bar */}
      <div className="px-4 py-2.5 bg-slate-900/40 border-b border-slate-800/80 overflow-x-auto whitespace-nowrap flex items-center gap-2">
        <span className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wider flex items-center gap-1 shrink-0">
          <Sparkles className="w-3.5 h-3.5" /> Suggestions:
        </span>
        {SUGGESTED_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(prompt)}
            disabled={loading}
            className="px-2.5 py-1 rounded-full text-xs bg-slate-800/80 hover:bg-indigo-600/30 text-slate-300 hover:text-white border border-slate-700/60 hover:border-indigo-500/40 transition-all shrink-0"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 max-w-3xl ${
              msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-7 h-7 rounded-lg shrink-0 flex items-center justify-center text-xs font-bold ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-indigo-400 border border-slate-700'
              }`}
            >
              {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div
              className={`rounded-2xl p-4 text-xs sm:text-sm leading-relaxed shadow-lg ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white rounded-tr-none'
                  : 'bg-slate-900/90 text-slate-200 border border-slate-800 rounded-tl-none'
              }`}
            >
              <div className="whitespace-pre-wrap prose prose-invert max-w-none text-xs sm:text-sm">
                {msg.text}
              </div>

              {/* Interactive action buttons returned by AI */}
              {msg.suggested_actions && msg.suggested_actions.length > 0 && (
                <div className="mt-3.5 pt-3 border-t border-slate-800 flex flex-wrap gap-2">
                  {msg.suggested_actions.map((act, i) => (
                    <button
                      key={i}
                      onClick={() => handleActionClick(act)}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/40 inline-flex items-center gap-1.5 transition-colors"
                    >
                      {act.label} <ArrowRight className="w-3 h-3" />
                    </button>
                  ))}
                </div>
              )}

              <span className="text-[10px] text-slate-400 mt-2 block text-right">
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 max-w-xl mr-auto">
            <div className="w-7 h-7 rounded-lg shrink-0 flex items-center justify-center bg-slate-800 text-indigo-400 border border-slate-700">
              <Bot className="w-4 h-4" />
            </div>
            <div className="rounded-2xl rounded-tl-none p-3.5 bg-slate-900/90 border border-slate-800 flex items-center gap-2 text-xs text-indigo-300">
              <div className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
              <span>Analyzing business database & reasoning...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/70">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask about invoices, overdue payments, tasks, or prepare emails..."
            disabled={loading}
            className="flex-1 bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
          />
          <Button
            type="submit"
            disabled={!inputMessage.trim() || loading}
            loading={loading}
            icon={Send}
            size="md"
          >
            Send
          </Button>
        </form>
      </div>
    </div>
  );
};

export default CommandCenterPage;
