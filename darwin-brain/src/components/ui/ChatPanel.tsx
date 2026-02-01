import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDarwinStore } from '../../store/darwinStore';
import { darwinApi, API_URL } from '../../utils/api';

const moodStyles = {
  curious: 'border-cyan-500/30 bg-cyan-500/5',
  excited: 'border-pink-500/30 bg-pink-500/5',
  contemplative: 'border-indigo-500/30 bg-indigo-500/5',
  focused: 'border-green-500/30 bg-green-500/5',
  mischievous: 'border-orange-500/30 bg-orange-500/5',
  caffeinated: 'border-yellow-500/30 bg-yellow-500/5',
  tired: 'border-gray-500/30 bg-gray-500/5',
  grumpy: 'border-red-500/30 bg-red-500/5',
  neutral: 'border-gray-500/30 bg-gray-500/5',
};

export function ChatPanel() {
  const showChat = useDarwinStore((state) => state.showChat);
  const toggleChat = useDarwinStore((state) => state.toggleChat);
  const messages = useDarwinStore((state) => state.messages);
  const addMessage = useDarwinStore((state) => state.addMessage);
  const status = useDarwinStore((state) => state.status);
  const setIsSpeaking = useDarwinStore((state) => state.setIsSpeaking);

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load chat history on open
  useEffect(() => {
    if (showChat && messages.length === 0) {
      loadHistory();
    }
  }, [showChat]);

  const loadHistory = async () => {
    try {
      const data = await darwinApi.getChatHistory(30);
      if (data.history) {
        data.history.reverse().forEach((msg: { role: string; content: string; timestamp: string }) => {
          addMessage({
            id: Math.random().toString(36),
            role: msg.role as 'user' | 'darwin',
            content: msg.content,
            timestamp: new Date(msg.timestamp),
          });
        });
      }
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
    addMessage({
      id: Math.random().toString(36),
      role: 'user',
      content: userMessage,
      timestamp: new Date(),
    });

    setIsLoading(true);

    try {
      const response = await darwinApi.sendMessage(userMessage);

      // Add Darwin's response
      addMessage({
        id: Math.random().toString(36),
        role: 'darwin',
        content: response.response,
        timestamp: new Date(),
        mood: response.mood,
        hasVoice: response.voice_path != null,
        voicePath: response.voice_path,
      });

      // Play voice if available
      if (response.voice_path && audioRef.current) {
        playVoice(response.voice_path);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      addMessage({
        id: Math.random().toString(36),
        role: 'darwin',
        content: 'Hmm, something went wrong. My neural pathways seem a bit tangled. Try again?',
        timestamp: new Date(),
        mood: 'contemplative',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const playVoice = (voicePath: string) => {
    if (audioRef.current) {
      audioRef.current.src = `${API_URL}${voicePath}`;
      setIsSpeaking(true);
      audioRef.current.play().catch(console.error);
    }
  };

  const handleAudioEnd = () => {
    setIsSpeaking(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <audio ref={audioRef} onEnded={handleAudioEnd} />

      <AnimatePresence>
        {showChat && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-4 top-20 bottom-4 w-96 z-40"
          >
            <div className="h-full glass rounded-2xl flex flex-col overflow-hidden">
              {/* Header */}
              <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xl">💬</span>
                  <div>
                    <h3 className="font-semibold text-white">Chat with Darwin</h3>
                    <p className="text-xs text-gray-400">
                      Feeling {status.mood} today
                    </p>
                  </div>
                </div>
                <button
                  onClick={toggleChat}
                  className="p-1 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <span className="text-gray-400">✕</span>
                </button>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.length === 0 && (
                  <div className="text-center text-gray-500 mt-8">
                    <span className="text-4xl mb-2 block">🧠</span>
                    <p>Start a conversation with Darwin</p>
                    <p className="text-sm mt-1">Ask anything about what I'm thinking!</p>
                  </div>
                )}

                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ y: 10, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-cyan-600 text-white rounded-br-sm'
                          : `border ${moodStyles[msg.mood || 'neutral']} rounded-bl-sm`
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

                      <div className="flex items-center justify-between mt-1 text-xs opacity-60">
                        <span>
                          {msg.timestamp.toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        {msg.hasVoice && (
                          <button
                            onClick={() => msg.voicePath && playVoice(msg.voicePath)}
                            className="ml-2 hover:opacity-100 transition-opacity"
                            title="Play voice"
                          >
                            🔊
                          </button>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}

                {isLoading && (
                  <motion.div
                    initial={{ y: 10, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    className="flex justify-start"
                  >
                    <div className="bg-gray-800/50 rounded-2xl rounded-bl-sm px-4 py-3">
                      <div className="flex gap-1">
                        <motion.span
                          animate={{ y: [0, -5, 0] }}
                          transition={{ repeat: Infinity, duration: 0.6, delay: 0 }}
                          className="w-2 h-2 bg-cyan-500 rounded-full"
                        />
                        <motion.span
                          animate={{ y: [0, -5, 0] }}
                          transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }}
                          className="w-2 h-2 bg-cyan-500 rounded-full"
                        />
                        <motion.span
                          animate={{ y: [0, -5, 0] }}
                          transition={{ repeat: Infinity, duration: 0.6, delay: 0.4 }}
                          className="w-2 h-2 bg-cyan-500 rounded-full"
                        />
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-4 border-t border-white/10">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask Darwin anything..."
                    className="flex-1 bg-gray-800/50 border border-white/10 rounded-xl px-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 transition-colors"
                    disabled={isLoading}
                  />
                  <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-xl transition-colors"
                  >
                    <span>→</span>
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default ChatPanel;
