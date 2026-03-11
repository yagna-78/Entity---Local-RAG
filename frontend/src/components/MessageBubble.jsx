
import ReactMarkdown from 'react-markdown';
import { User, Bot, Copy, Check, Reply } from 'lucide-react';
import { useState } from 'react';
import { motion } from 'framer-motion';

const MessageBubble = ({ message, onReply }) => {
    const isUser = message.role === 'user';
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(message.content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`flex gap-4 max-w-4xl mx-auto w-full ${isUser ? 'flex-row-reverse' : ''}`}
        >
            {/* Avatar */}
            <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-lg ${isUser
                ? 'bg-gradient-to-br from-zinc-200 to-zinc-300 border border-zinc-300 dark:from-zinc-700 dark:to-zinc-900 dark:border-zinc-700'
                : 'bg-gradient-to-br from-red-500 to-red-600 border border-red-500/30 dark:from-red-600 dark:to-red-900'
                }`}>
                {isUser ? <User size={18} className="text-zinc-600 dark:text-zinc-300" /> : <Bot size={18} className="text-white" />}
            </div>


            {/* Content Group */}
            <div className={`relative flex-1 min-w-0 group flex ${isUser ? 'flex-col items-end' : 'flex-col items-start'}`}>

                {/* Message Bubble */}
                <div className={`relative px-6 py-4 rounded-2xl shadow-xl backdrop-blur-sm border max-w-full ${isUser
                    ? 'bg-white text-zinc-800 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-100 dark:border-zinc-700/50 rounded-tr-none'
                    : 'bg-white/80 text-zinc-800 border-zinc-200 dark:bg-black/40 dark:text-zinc-200 dark:border-zinc-800/50 rounded-tl-none'
                    }`}>

                    {/* Header Name */}
                    <div className={`text-xs font-bold mb-2 uppercase tracking-wider ${isUser ? 'text-zinc-500 text-right' : 'text-red-500 dark:text-red-500/80'
                        }`}>
                        {isUser ? 'You' : (
                            <span className="flex items-center gap-2">
                                Entity

                            </span>
                        )}
                    </div>

                    <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-zinc-100 prose-pre:border prose-pre:border-zinc-200 dark:prose-invert dark:prose-pre:bg-zinc-950 dark:prose-pre:border-zinc-800 break-words mb-2">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>

                    {/* Actions - Inside Bubble */}
                    <div className={`flex gap-2 mt-2 pt-2 border-t border-zinc-200 dark:border-white/5 ${isUser ? 'justify-end' : 'justify-start'}`}>
                        {onReply && (
                            <button
                                onClick={() => onReply(message)}
                                className="flex items-center gap-1.5 px-2 py-1 hover:bg-zinc-100 dark:hover:bg-white/10 rounded text-xs font-medium text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
                                title="Reply"
                            >
                                <Reply size={12} />
                                <span>Reply</span>
                            </button>
                        )}
                        {!isUser && (
                            <button
                                onClick={handleCopy}
                                className="flex items-center gap-1.5 px-2 py-1 hover:bg-zinc-100 dark:hover:bg-white/10 rounded text-xs font-medium text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
                                title="Copy"
                            >
                                {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
                                <span>{copied ? 'Copied' : 'Copy'}</span>
                            </button>
                        )}
                    </div>
                </div>

            </div>


        </motion.div>
    );
};

export default MessageBubble;
