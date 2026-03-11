import React, { useRef, useEffect } from 'react';
import { Send, Sparkles, X, BarChart3, Users, PieChart, Zap } from 'lucide-react';
import MessageBubble from './MessageBubble';
import { motion, AnimatePresence } from 'framer-motion';
import EntityLogo from './EntityLogo';

const WelcomeScreen = ({ onAction }) => {
    return (
        <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto px-4 text-center">
            <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-3 tracking-tight mt-6">
                Welcome to Entity
            </h1>
            <p className="text-zinc-600 dark:text-zinc-400 text-lg mb-12 max-w-lg">
                Your secure, local AI assistant. Ask about your data, documents, or anything else.
            </p>

            {/* Action Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-xl">
                <button
                    onClick={() => onAction("Show Revenue")}
                    className="flex items-center gap-4 p-4 text-left bg-white/50 dark:bg-zinc-800/50 hover:bg-white dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/50 rounded-2xl transition-all hover:scale-[1.02] group"
                >
                    <div className="p-3 bg-indigo-500/10 text-indigo-500 rounded-xl group-hover:bg-indigo-500 group-hover:text-white transition-colors">
                        <BarChart3 size={20} />
                    </div>
                    <div>
                        <span className="block font-semibold text-slate-900 dark:text-zinc-100">Show Revenue</span>
                        <span className="text-xs text-zinc-500 dark:text-zinc-500">Analyze financial performance</span>
                    </div>
                </button>

                <button
                    onClick={() => onAction("Team Overview")}
                    className="flex items-center gap-4 p-4 text-left bg-white/50 dark:bg-zinc-800/50 hover:bg-white dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/50 rounded-2xl transition-all hover:scale-[1.02] group"
                >
                    <div className="p-3 bg-purple-500/10 text-purple-500 rounded-xl group-hover:bg-purple-500 group-hover:text-white transition-colors">
                        <Users size={20} />
                    </div>
                    <div>
                        <span className="block font-semibold text-slate-900 dark:text-zinc-100">Team Overview</span>
                        <span className="text-xs text-zinc-500 dark:text-zinc-500">Staffing and resource allocation</span>
                    </div>
                </button>

                <button
                    onClick={() => onAction("Expense Breakdown")}
                    className="flex items-center gap-4 p-4 text-left bg-white/50 dark:bg-zinc-800/50 hover:bg-white dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/50 rounded-2xl transition-all hover:scale-[1.02] group"
                >
                    <div className="p-3 bg-pink-500/10 text-pink-500 rounded-xl group-hover:bg-pink-500 group-hover:text-white transition-colors">
                        <PieChart size={20} />
                    </div>
                    <div>
                        <span className="block font-semibold text-slate-900 dark:text-zinc-100">Expense Breakdown</span>
                        <span className="text-xs text-zinc-500 dark:text-zinc-500">Track spending across projects</span>
                    </div>
                </button>

                <button
                    onClick={() => onAction("Active Projects")}
                    className="flex items-center gap-4 p-4 text-left bg-white/50 dark:bg-zinc-800/50 hover:bg-white dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/50 rounded-2xl transition-all hover:scale-[1.02] group"
                >
                    <div className="p-3 bg-yellow-500/10 text-yellow-500 rounded-xl group-hover:bg-yellow-500 group-hover:text-white transition-colors">
                        <Zap size={20} />
                    </div>
                    <div>
                        <span className="block font-semibold text-slate-900 dark:text-zinc-100">Active Projects</span>
                        <span className="text-xs text-zinc-500 dark:text-zinc-500">Status and timeline updates</span>
                    </div>
                </button>
            </div>
        </div>
    );
};

// --- Dashboard Modal Component ---
const DashboardModal = ({ isOpen, onClose, title, data, type, isLoading }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
            <div className="bg-white dark:bg-zinc-900 w-full max-w-2xl rounded-3xl shadow-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden flex flex-col max-h-[80vh]" onClick={e => e.stopPropagation()}>

                {/* Header */}
                <div className="p-6 border-b border-zinc-100 dark:border-zinc-800 flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                            {type === 'revenue' && <BarChart3 className="text-indigo-500" />}
                            {type === 'team' && <Users className="text-purple-500" />}
                            {type === 'expenses' && <PieChart className="text-pink-500" />}
                            {type === 'projects' && <Zap className="text-yellow-500" />}
                            {title}
                        </h2>
                        {data?.period && <p className="text-sm text-zinc-500 mt-1">Period: {data.period}</p>}
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors">
                        <X className="w-6 h-6 text-zinc-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-12 space-y-4">
                            <Sparkles className="w-8 h-8 text-indigo-500 animate-spin" />
                            <p className="text-zinc-500 animate-pulse">Fetching latest data...</p>
                        </div>
                    ) : data?.error ? (
                        <div className="flex flex-col items-center justify-center py-12 space-y-4 text-center">
                            <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-500 rounded-full">
                                <X size={32} />
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Failed to load data</h3>
                            <p className="text-zinc-500 max-w-xs">{data.error}</p>
                            <button
                                onClick={onClose}
                                className="mt-4 px-4 py-2 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-lg hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    ) : (
                        <>
                            {/* REVENUE VIEW */}
                            {type === 'revenue' && data && (
                                <div className="space-y-6">
                                    <div className="bg-indigo-500/10 p-6 rounded-2xl flex items-center justify-between">
                                        <span className="text-indigo-600 dark:text-indigo-400 font-medium">Total Revenue</span>
                                        <span className="text-3xl font-bold text-indigo-700 dark:text-indigo-300">
                                            ₹{data.total_revenue?.toLocaleString()}
                                        </span>
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-wider mb-4">Revenue by Source</h3>
                                        <div className="space-y-3">
                                            {data.breakdown?.map((item, idx) => (
                                                <div key={idx} className="flex items-center justify-between p-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 rounded-xl transition-colors">
                                                    <span className="font-medium text-slate-700 dark:text-zinc-300">{item.source}</span>
                                                    <span className="font-semibold text-slate-900 dark:text-white">₹{item.amount?.toLocaleString()}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* TEAM VIEW */}
                            {type === 'team' && data && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {data.team?.map((member, idx) => (
                                        <div key={idx} className="p-4 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-zinc-50/50 dark:bg-zinc-800/20">
                                            <div className="flex justify-between items-start mb-2">
                                                <div>
                                                    <h3 className="font-bold text-slate-900 dark:text-white">{member.name}</h3>
                                                    <p className="text-xs text-zinc-500">{member.role}</p>
                                                </div>
                                                <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400 font-bold text-xs">
                                                    {member.name.charAt(0)}
                                                </div>
                                            </div>
                                            <div className="space-y-1 mt-3">
                                                {member.projects?.length > 0 ? (
                                                    member.projects.map((p, pIdx) => (
                                                        <div key={pIdx} className="text-xs px-2 py-1 bg-white dark:bg-zinc-800 rounded border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400">
                                                            <span>{p.name}</span>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <span className="text-xs text-zinc-400 italic">No active projects</span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* EXPENSES VIEW */}
                            {type === 'expenses' && data && (
                                <div className="space-y-6">
                                    <div className="bg-pink-500/10 p-6 rounded-2xl flex items-center justify-between">
                                        <span className="text-pink-600 dark:text-pink-400 font-medium">Total Expenses</span>
                                        <span className="text-3xl font-bold text-pink-700 dark:text-pink-300">
                                            ₹{data.total_expenses?.toLocaleString()}
                                        </span>
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-wider mb-4">Breakdown by Category</h3>
                                        <div className="space-y-3">
                                            {data.breakdown?.map((item, idx) => (
                                                <div key={idx} className="flex items-center justify-between p-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 rounded-xl transition-colors group">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-pink-400 group-hover:scale-125 transition-transform" />
                                                        <span className="font-medium text-slate-700 dark:text-zinc-300">{item.category}</span>
                                                    </div>
                                                    <span className="font-semibold text-slate-900 dark:text-white">₹{item.amount?.toLocaleString()}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* PROJECTS VIEW */}
                            {type === 'projects' && data && (
                                <div className="space-y-4">
                                    {data.active_projects?.map((project, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-4 border border-zinc-200 dark:border-zinc-800 rounded-2xl hover:border-yellow-400/50 transition-colors">
                                            <div>
                                                <h3 className="font-bold text-slate-900 dark:text-white">{project.name}</h3>
                                                <p className="text-sm text-zinc-500">{project.client}</p>
                                            </div>
                                            <div className="text-right">
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-500">
                                                    In Progress
                                                </span>
                                                <p className="text-xs text-zinc-400 mt-1">Due: {project.deadline}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

const ChatView = ({
    messages,
    input,
    setInput,
    isLoading,
    handleSend,
    handleStop,
    replyTo,
    setReplyTo,
    messagesEndRef
}) => {
    // Modal State
    const [modalOpen, setModalOpen] = React.useState(false);
    const [modalData, setModalData] = React.useState(null);
    const [modalType, setModalType] = React.useState('');
    const [modalLoading, setModalLoading] = React.useState(false);
    const [modalTitle, setModalTitle] = React.useState('');

    // Action Handler
    const handleDashboardAction = async (actionName) => {
        setModalOpen(true);
        setModalLoading(true);
        setModalData(null);
        setModalTitle(actionName); // Set title immediately

        let endpoint = '';
        let type = '';

        switch (actionName) {
            case "Show Revenue":
                endpoint = '/dashboard/revenue';
                type = 'revenue';
                break;
            case "Team Overview":
                endpoint = '/dashboard/team';
                type = 'team';
                break;
            case "Expense Breakdown":
                endpoint = '/dashboard/expenses';
                type = 'expenses';
                break;
            case "Active Projects":
                endpoint = '/dashboard/projects';
                type = 'projects';
                break;
            default:
                // Fallback to chat if not a dashboard action
                handleSend(actionName);
                setModalOpen(false);
                return;
        }

        setModalType(type);

        try {
            // FIXED: Changed port from 8001 to 8000 to match backend
            const res = await fetch(`http://localhost:8000${endpoint}`);
            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}));
                throw new Error(errorData.detail || `Server error: ${res.status}`);
            }
            const data = await res.json();
            setModalData(data);
        } catch (err) {
            console.error("Dashboard Fetch Error:", err);
            setModalData({ error: err.message }); // Pass error to modal
        } finally {
            setModalLoading(false);
        }
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, messagesEndRef]);

    return (
        <div className="h-full flex flex-col overflow-hidden relative">
            {/* Dashboard Modal */}
            <DashboardModal
                isOpen={modalOpen}
                onClose={() => setModalOpen(false)}
                title={modalTitle}
                data={modalData}
                type={modalType}
                isLoading={modalLoading}
            />

            {/* Chat Window */}
            <div className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth w-full" id="chat-container">
                <div className="max-w-4xl mx-auto space-y-8 pb-4">
                    {messages.length === 0 ? (
                        <WelcomeScreen onAction={handleDashboardAction} />
                    ) : (
                        <>
                            {messages.map((msg, idx) => (
                                <MessageBubble
                                    key={idx}
                                    message={msg}
                                    onReply={(msg) => {
                                        setReplyTo(msg);
                                        document.querySelector('input[type="text"]')?.focus();
                                    }}
                                />
                            ))}
                            {isLoading && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="flex items-center gap-2 text-zinc-500 text-sm ml-16"
                                    layout
                                >
                                    <Sparkles size={14} className="animate-spin" /> Thinking...
                                </motion.div>
                            )}
                            <div ref={messagesEndRef} />
                        </>
                    )}
                </div>
            </div>

            {/* Input Area */}
            <div className="shrink-0 p-4 md:p-6 bg-transparent z-20 w-full">
                <div className="max-w-4xl mx-auto relative space-y-2">

                    {/* Reply Preview */}
                    <AnimatePresence>
                        {replyTo && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: 10 }}
                                className="bg-white/80 dark:bg-zinc-800/80 backdrop-blur-md rounded-xl p-3 border-l-4 border-red-500 flex justify-between items-start shadow-lg mb-2"
                            >
                                <div className="text-sm">
                                    <span className="font-bold text-red-400 text-xs uppercase mb-1 block">
                                        Replying to {replyTo.role === 'user' ? 'You' : 'Entity'}
                                    </span>
                                    <p className="text-zinc-600 dark:text-zinc-300 line-clamp-1">{replyTo.content}</p>
                                </div>
                                <button
                                    onClick={() => setReplyTo(null)}
                                    className="p-1 hover:bg-zinc-700 rounded-full text-zinc-500 hover:text-white transition-colors"
                                >
                                    <X size={14} />
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <div className="relative flex items-center bg-white dark:bg-zinc-900/50 shadow-xl backdrop-blur-md rounded-2xl overflow-hidden border border-zinc-200 dark:border-zinc-800 focus-within:border-zinc-400 dark:focus-within:border-zinc-600 focus-within:ring-1 focus-within:ring-zinc-400 dark:focus-within:ring-zinc-600 transition-all">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleSend()}
                            placeholder="Ask anything about your data..."
                            className="w-full bg-transparent border-0 px-6 py-4 text-zinc-800 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:ring-0 focus:outline-none"
                            disabled={isLoading}
                        />
                        {isLoading ? (
                            <button
                                onClick={handleStop}
                                className="p-4 text-red-500 hover:text-red-400 transition-colors animate-pulse"
                                title="Stop Generating"
                            >
                                <div className="w-5 h-5 bg-current rounded-sm" />
                            </button>
                        ) : (
                            <button
                                onClick={handleSend}
                                disabled={!input.trim()}
                                className="p-4 text-zinc-400 hover:text-zinc-600 dark:hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <Send size={20} />
                            </button>
                        )}
                    </div>
                    <p className="text-center text-zinc-500 dark:text-zinc-600 text-xs mt-1">
                        Entity runs locally. Responses are generated from your documents and database.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default ChatView;
