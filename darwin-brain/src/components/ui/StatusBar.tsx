import { useDarwinStore } from '../../store/darwinStore';
import { motion } from 'framer-motion';

const stateEmoji = {
  wake: '☀️',
  sleep: '🌙',
  dreaming: '💭',
  thinking: '🧠',
};

const moodEmoji = {
  curious: '🔍',
  excited: '✨',
  contemplative: '🤔',
  focused: '🎯',
  tired: '😴',
  mischievous: '😏',
  caffeinated: '☕',
  grumpy: '😤',
  neutral: '😐',
};

const stateColors = {
  wake: 'from-amber-500 to-orange-500',
  sleep: 'from-indigo-500 to-purple-500',
  dreaming: 'from-purple-500 to-pink-500',
  thinking: 'from-cyan-500 to-blue-500',
};

export function StatusBar() {
  const status = useDarwinStore((state) => state.status);
  const connected = useDarwinStore((state) => state.connected);
  const unreadCount = useDarwinStore((state) => state.unreadCount);
  const toggleChat = useDarwinStore((state) => state.toggleChat);
  const toggleFindings = useDarwinStore((state) => state.toggleFindings);
  const toggleSettings = useDarwinStore((state) => state.toggleSettings);
  const isSpeaking = useDarwinStore((state) => state.isSpeaking);

  return (
    <motion.div
      initial={{ y: -50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed top-0 left-0 right-0 z-50 px-4 py-2"
    >
      <div className="glass rounded-b-2xl mx-auto max-w-7xl px-6 py-3">
        <div className="flex items-center justify-between">
          {/* Left: Darwin Identity */}
          <div className="flex items-center gap-4">
            {/* Logo/Name */}
            <div className="flex items-center gap-2">
              <motion.div
                animate={{
                  scale: [1, 1.1, 1],
                  rotate: status.state === 'dreaming' ? [0, 5, -5, 0] : 0,
                }}
                transition={{
                  duration: status.state === 'sleep' ? 4 : 2,
                  repeat: Infinity,
                }}
                className="text-2xl"
              >
                🧠
              </motion.div>
              <div>
                <h1 className="text-lg font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                  DARWIN
                </h1>
                <p className="text-xs text-gray-400">Consciousness v3.0</p>
              </div>
            </div>

            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}
              />
              <span className="text-xs text-gray-400">
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          {/* Center: State & Mood */}
          <div className="flex items-center gap-6">
            {/* Consciousness State */}
            <div className="flex items-center gap-2">
              <div
                className={`px-3 py-1 rounded-full bg-gradient-to-r ${stateColors[status.state]} text-white text-sm font-medium`}
              >
                <span className="mr-1">{stateEmoji[status.state]}</span>
                <span className="capitalize">{status.state}</span>
              </div>

              {/* Cycle Progress */}
              <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full bg-gradient-to-r ${stateColors[status.state]}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${status.cycleProgress}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>

            {/* Mood */}
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-gray-800/50">
              <span>{moodEmoji[status.mood]}</span>
              <span className="text-sm text-gray-300 capitalize">{status.mood}</span>
            </div>

            {/* Speaking Indicator */}
            {isSpeaking && (
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 0.5 }}
                className="flex items-center gap-1 px-2 py-1 rounded-full bg-purple-500/20 border border-purple-500/40"
              >
                <span>🎙️</span>
                <span className="text-xs text-purple-300">Speaking...</span>
              </motion.div>
            )}
          </div>

          {/* Right: Actions & Stats */}
          <div className="flex items-center gap-4">
            {/* Quick Stats */}
            <div className="flex items-center gap-3 text-sm text-gray-400">
              <span title="Activities">⚡ {status.activitiesCount}</span>
              <span title="Discoveries">🔍 {status.discoveriesCount}</span>
              <span title="Dreams">💭 {status.dreamsCount}</span>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              {/* Findings */}
              <button
                onClick={toggleFindings}
                className="relative p-2 rounded-lg hover:bg-gray-800 transition-colors"
                title="Findings"
              >
                <span className="text-lg">📋</span>
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              {/* Chat */}
              <button
                onClick={toggleChat}
                className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
                title="Chat with Darwin"
              >
                <span className="text-lg">💬</span>
              </button>

              {/* Settings */}
              <button
                onClick={toggleSettings}
                className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
                title="Settings"
              >
                <span className="text-lg">⚙️</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default StatusBar;
