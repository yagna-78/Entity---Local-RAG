import { useState, useRef, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import KPIDashboard from './pages/KPIDashboard';
import { X, Lightbulb, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Wrapper for main content to handle layout
const MainLayout = ({ children, isSidebarOpen, setIsSidebarOpen, ...sidebarProps }) => {
  const { theme } = useTheme();

  return (
    <div className={`flex h-[125vh] font-sans overflow-hidden transition-colors duration-500 ${theme === 'dark' ? 'bg-grid-depth text-gray-100' : 'bg-grid-depth-light text-slate-900'}`}>


      <Sidebar
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        {...sidebarProps}
      />

      {/* Main Content Area */}
      <main className={`flex-1 flex flex-col transition-all duration-300 relative z-10 ${isSidebarOpen || window.innerWidth >= 768 ? 'md:ml-80' : ''} h-[125vh] overflow-hidden`}>
        {children}
      </main>
    </div>
  );
};

function App() {
  // --- Chat State (Lifted) ---
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [replyTo, setReplyTo] = useState(null);

  // Settings
  const [model, setModel] = useState('mistral:latest');


  // Tip of the Day
  const [isTipOpen, setIsTipOpen] = useState(false);
  const [dailyTip, setDailyTip] = useState(null);

  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  // --- Handlers ---

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
      setMessages(prev => {
        const newMsg = [...prev];
        if (newMsg.length > 0 && newMsg[newMsg.length - 1].role === 'assistant') {
          newMsg[newMsg.length - 1].content += "\n\n*[Generation stopped by user]*";
        }
        return newMsg;
      });
    }
  };

  const handleSend = async (manualInput = null) => {
    const textToSend = manualInput || input;
    if (!textToSend.trim() || isLoading) return;

    let contentToSend = textToSend;
    if (replyTo) {
      contentToSend = `> **Replying to ${replyTo.role === 'user' ? 'You' : 'Entity'}:**\n> ${replyTo.content.substring(0, 150)}...\n\n${textToSend}`;
    }

    const userMessage = { role: 'user', content: contentToSend };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setReplyTo(null);
    setIsLoading(true);

    abortControllerRef.current = new AbortController();

    try {
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage.content,
          model: model,
          mode: 'qa',
          history: messages.filter(m => m.content)
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        aiContent += chunk;

        setMessages(prev => {
          const newMsg = [...prev];
          newMsg[newMsg.length - 1] = { role: 'assistant', content: aiContent };
          return newMsg;
        });
      }

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Fetch aborted');
      } else {
        console.error(error);
        setMessages(prev => [...prev, { role: 'assistant', content: `**Error:** ${error.message}` }]);
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const loadingId = Date.now();
      setMessages(prev => [...prev, { role: 'assistant', content: `Uploading **${file.name}**...` }]);

      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        setMessages(prev => {
          const newMsg = [...prev];
          newMsg[newMsg.length - 1] = { role: 'assistant', content: `✅ I've processed **${file.name}**. My knowledge base now has ${data.count} chunks.` };
          return newMsg;
        });
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ Upload Failed: ${error.message}` }]);
    }
  };

  const handleReload = async () => {
    if (!confirm("Revisit all documents? This might take a moment.")) return;

    setMessages(prev => [...prev, { role: 'assistant', content: `🔄 Re-indexing database...` }]);
    try {
      const res = await fetch('http://localhost:8000/ingest', { method: 'POST' });
      if (res.ok) {
        setMessages(prev => [...prev, { role: 'assistant', content: `✅ Database updated successfully.` }]);
      } else {
        throw new Error("Failed");
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ Indexing failed.` }]);
    }
  };

  const handleExport = () => {
    const text = messages.map(m => `${m.role.toUpperCase()}: ${m.content}`).join('\n\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chat-history.txt';
    a.click();
  };

  const handleShowTip = async () => {
    try {
      setIsTipOpen(true);
      if (!dailyTip) {
        const res = await fetch('http://localhost:8000/daily-tip');
        const data = await res.json();
        setDailyTip(data);
      }
    } catch (e) {
      console.error("Failed to fetch tip", e);
      setDailyTip({ tip: "Could not load tip at this time.", pattern: "Connection Error", severity: 0 });
    }
  };

  return (
    <ThemeProvider>
      <BrowserRouter>
        <MainLayout
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          model={model}
          setModel={setModel}
          onUpload={handleUpload}
          onReload={handleReload}
          onClear={() => setMessages([])}
          onExport={handleExport}
          onTip={handleShowTip}
        >
          <Routes>
            <Route path="/" element={
              <ChatView
                messages={messages}
                input={input}
                setInput={setInput}
                isLoading={isLoading}
                handleSend={handleSend}
                handleStop={handleStop}
                replyTo={replyTo}
                setReplyTo={setReplyTo}
                messagesEndRef={messagesEndRef}
              />
            } />
            <Route path="/dashboard" element={<KPIDashboard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>

          {/* Global Tip Modal - Accessible from anywhere */}
          <AnimatePresence>
            {isTipOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 dark:bg-black/60 backdrop-blur-sm">
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.9, opacity: 0 }}
                  className="bg-white dark:bg-zinc-900 border border-yellow-400/40 dark:border-yellow-500/30 rounded-2xl p-6 max-w-md w-full shadow-2xl relative overflow-hidden"
                >
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-yellow-500 to-yellow-400" />
                  <button
                    onClick={() => setIsTipOpen(false)}
                    className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-900 dark:text-zinc-500 dark:hover:text-white z-10"
                  >
                    <X size={20} />
                  </button>

                  {!dailyTip ? (
                    <div className="flex flex-col items-center justify-center py-10 space-y-4">
                      <Sparkles className="w-8 h-8 text-yellow-500 animate-spin" />
                      <p className="text-zinc-500 dark:text-zinc-400 text-sm">Consulting Strategy Engine...</p>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center gap-3 mb-4">
                        <div className="p-3 bg-yellow-500/10 rounded-full text-yellow-500">
                          <Lightbulb size={24} />
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-zinc-900 dark:text-white">Tip of the Day</h3>
                          <p className="text-xs text-zinc-500 uppercase tracking-wider">{dailyTip.date}</p>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div className="p-4 bg-zinc-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200 dark:border-zinc-700/50">
                          <p className="text-zinc-800 dark:text-zinc-200 text-lg leading-relaxed font-medium">
                            "{dailyTip.tip}"
                          </p>
                        </div>

                        <div className="flex items-center justify-between text-sm">
                          <span className="text-zinc-500">Trigger: <span className="text-yellow-600 dark:text-yellow-500/80">{dailyTip.pattern}</span></span>
                          <span className="flex items-center gap-1 text-zinc-500">
                            Severity:
                            <div className="flex gap-0.5">
                              {[...Array(10)].map((_, i) => (
                                <div key={i} className={`w-1 h-3 rounded-full ${i < dailyTip.severity ? 'bg-red-500' : 'bg-zinc-300 dark:bg-zinc-700'}`} />
                              ))}
                            </div>
                          </span>
                        </div>
                      </div>
                    </>
                  )}
                </motion.div>
              </div>
            )}
          </AnimatePresence>

        </MainLayout>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
