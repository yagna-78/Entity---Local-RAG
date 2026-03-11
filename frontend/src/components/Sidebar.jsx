import { Upload, RefreshCw, Trash2, Download, Menu, X, BrainCircuit, Globe, Zap, LayoutDashboard, MessageSquare, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import EntityLogo from './EntityLogo';

const Sidebar = ({
    isOpen,
    setIsOpen,
    model,
    setModel,
    onUpload,
    onReload,
    onClear,
    onExport,
    onTip
}) => {
    const location = useLocation();
    const isChat = location.pathname === '/';
    const { theme, toggleTheme } = useTheme();

    return (
        <>
            {/* Mobile Toggle */}
            <div className="md:hidden fixed top-4 left-4 z-50">
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="p-2 bg-white dark:bg-zinc-900 border border-red-900/30 text-red-500 rounded-lg shadow-lg shadow-red-900/20"
                >
                    {isOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
            </div>

            {/* Sidebar Container */}
            <AnimatePresence>
                {(isOpen || window.innerWidth >= 768) && (
                    <motion.div
                        initial={{ x: -300, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: -300, opacity: 0 }}
                        className={`fixed top-2.5 h-[calc(125vh-1.25rem)] left-0 w-80 bg-white/40 dark:bg-black/20 border-r border-white/20 dark:border-white/5 backdrop-blur-[2px] z-40 flex flex-col p-6 shadow-2xl shadow-red-900/5 rounded-r-3xl transition-colors duration-300 ${!isOpen && 'hidden md:flex'}`}
                    >
                        {/* Header */}
                        <div className="flex flex-col items-center justify-center mb-12 mt-8 w-full overflow-hidden">
                            <EntityLogo className="scale-[0.6] origin-top" />
                        </div>

                        {/* Navigation */}
                        <div className="space-y-2 mb-8">
                            <Link
                                to="/"
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${isChat ? 'bg-red-500/10 text-red-600 dark:text-red-500 border border-red-500/20' : 'text-zinc-700 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-200/50 dark:hover:bg-zinc-900'}`}
                            >
                                <MessageSquare size={18} />
                                <span className="font-medium tracking-wide">Assistant</span>
                            </Link>
                            <Link
                                to="/dashboard"
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${!isChat ? 'bg-red-500/10 text-red-600 dark:text-red-500 border border-red-500/20' : 'text-zinc-700 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-200/50 dark:hover:bg-zinc-900'}`}
                            >
                                <LayoutDashboard size={18} />
                                <span className="font-medium tracking-wide">Executive Dashboard</span>
                            </Link>
                        </div>

                        {/* Controls - Only show relevant controls based on view */}
                        <div className="space-y-6 flex-1 text-sm overflow-y-auto pr-1 custom-scrollbar">

                            {isChat && (
                                <>
                                    <div className="space-y-2">
                                        <label className="text-zinc-600 dark:text-zinc-500 text-xs uppercase font-bold tracking-wider ml-1">AI Model</label>
                                        <div className="relative">
                                            <Globe className="absolute left-3 top-3 text-red-500 w-4 h-4" />
                                            <select
                                                value={model}
                                                onChange={(e) => setModel(e.target.value)}
                                                className="w-full bg-zinc-100 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-xl py-2.5 pl-10 pr-4 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all appearance-none cursor-pointer hover:bg-zinc-200 dark:hover:bg-zinc-900"
                                            >
                                                <option value="mistral:latest">Mistral (Latest)</option>
                                            </select>
                                        </div>
                                    </div>


                                </>
                            )}

                            {/* Actions Divider */}
                            <div className="h-px bg-gradient-to-r from-transparent via-zinc-800 to-transparent my-4" />

                            <div className="grid grid-cols-1 gap-3">
                                {/* Global Actions */}
                                <button
                                    onClick={() => document.getElementById('file-upload').click()}
                                    className="group flex items-center justify-between p-3 rounded-xl transition-all hover:bg-zinc-100 dark:hover:bg-zinc-800/80"
                                >
                                    <span className="flex items-center gap-3 text-zinc-300 group-hover:text-white">
                                        <div className="p-1.5 rounded-lg bg-zinc-200 dark:bg-zinc-800/50 group-hover:bg-red-500/10 transition-colors">
                                            <Upload size={16} className="text-zinc-600 dark:text-zinc-400 group-hover:text-red-500 transition-colors" />
                                        </div>
                                        <span className="text-zinc-700 dark:text-zinc-300 group-hover:text-zinc-950 dark:group-hover:text-white font-medium">Upload Doc</span>
                                    </span>
                                </button>
                                <input
                                    type="file"
                                    id="file-upload"
                                    className="hidden"
                                    accept=".txt,.pdf"
                                    onChange={onUpload}
                                />

                                <button
                                    onClick={onReload}
                                    className="group flex items-center justify-between p-3 rounded-xl transition-all hover:bg-zinc-200/50 dark:hover:bg-zinc-800/80"
                                >
                                    <span className="flex items-center gap-3 text-zinc-300 group-hover:text-white">
                                        <div className="p-1.5 rounded-lg bg-zinc-200 dark:bg-zinc-800/50 group-hover:bg-green-500/10 transition-colors">
                                            <RefreshCw size={16} className="text-zinc-600 dark:text-zinc-400 group-hover:text-green-500 transition-colors" />
                                        </div>
                                        <span className="text-zinc-700 dark:text-zinc-300 group-hover:text-zinc-950 dark:group-hover:text-white font-medium">re-Index DB</span>
                                    </span>
                                </button>

                                <button
                                    onClick={onTip}
                                    className="group flex items-center justify-between p-3 rounded-xl transition-all hover:bg-zinc-100 dark:hover:bg-zinc-800/80"
                                >
                                    <span className="flex items-center gap-3 text-zinc-300 group-hover:text-white">
                                        <div className="p-1.5 rounded-lg bg-zinc-200 dark:bg-zinc-800/50 group-hover:bg-yellow-500/10 transition-colors">
                                            <div className="relative">
                                                <div className="absolute -inset-1 bg-yellow-500/50 rounded-full blur-sm opacity-0 group-hover:opacity-100 transition-opacity" />
                                                <Zap size={16} className="relative text-zinc-600 dark:text-zinc-400 group-hover:text-yellow-500 transition-colors" />
                                            </div>
                                        </div>
                                        <span className="text-zinc-700 dark:text-zinc-300 group-hover:text-zinc-950 dark:group-hover:text-white font-medium">Tip of the Day</span>
                                    </span>
                                </button>

                                {isChat && (
                                    <button
                                        onClick={onExport}
                                        className="group flex items-center justify-between p-3 rounded-xl transition-all hover:bg-zinc-100 dark:hover:bg-zinc-800/80"
                                    >
                                        <span className="flex items-center gap-3 text-zinc-300 group-hover:text-white">
                                            <div className="p-1.5 rounded-lg bg-zinc-200 dark:bg-zinc-800/50 group-hover:bg-blue-500/10 transition-colors">
                                                <Download size={16} className="text-zinc-600 dark:text-zinc-400 group-hover:text-blue-500 transition-colors" />
                                            </div>
                                            <span className="text-zinc-700 dark:text-zinc-300 group-hover:text-zinc-950 dark:group-hover:text-white font-medium">Export Chat</span>
                                        </span>
                                    </button>
                                )}
                            </div>

                        </div>

                        {/* Footer */}
                        <div className="mt-auto pt-6 border-t border-zinc-200 dark:border-zinc-900 space-y-4">

                            {/* Theme Toggle */}
                            <button
                                onClick={toggleTheme}
                                className="w-full flex items-center justify-center gap-2 p-3 bg-zinc-200/50 dark:bg-zinc-800/50 text-zinc-700 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-zinc-200 rounded-xl transition-all text-sm font-medium"
                            >
                                {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                                {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
                            </button>

                            {isChat && (
                                <button
                                    onClick={onClear}
                                    className="w-full flex items-center justify-center gap-2 p-3 text-zinc-600 dark:text-zinc-500 hover:text-red-600 dark:hover:text-red-500 hover:bg-red-500/5 rounded-xl transition-all text-sm font-medium"
                                >
                                    <Trash2 size={16} />
                                    Clear Conversation
                                </button>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
};

export default Sidebar;
