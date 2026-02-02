import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDarwinStore } from '../../store/darwinStore';
import { api } from '../../utils/api';

interface ActivityLog {
  id: string;
  category: string;
  action: string;
  description: string;
  status: string;
  timestamp: string;
  duration_ms?: number;
  error?: string;
}

interface MonitorStats {
  total_activities: number;
  successful: number;
  failed: number;
  errors_last_hour: number;
  by_category: Record<string, number>;
  moltbook: {
    posts_read: number;
    posts_created: number;
    comments_made: number;
    upvotes_given: number;
  };
}

const categoryIcons: Record<string, string> = {
  moltbook: '🦞',
  internet: '🌐',
  thinking: '🧠',
  creating: '🛠️',
  executing: '⚡',
  system: '⚙️',
};

const categoryColors: Record<string, string> = {
  moltbook: 'text-orange-400 border-orange-500/30 bg-orange-500/10',
  internet: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
  thinking: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
  creating: 'text-green-400 border-green-500/30 bg-green-500/10',
  executing: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10',
  system: 'text-gray-400 border-gray-500/30 bg-gray-500/10',
};

const statusIcons: Record<string, string> = {
  success: '✅',
  failed: '❌',
  started: '🔄',
  partial: '⚠️',
};

export function MonitorPanel() {
  const showMonitor = useDarwinStore((state) => state.showMonitor);
  const toggleMonitor = useDarwinStore((state) => state.toggleMonitor);

  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [stats, setStats] = useState<MonitorStats | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [showErrors, setShowErrors] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const logsStartRef = useRef<HTMLDivElement>(null);

  // Fetch logs
  const fetchLogs = async () => {
    try {
      const categoryParam = filter !== 'all' ? `&category=${filter}` : '';
      const statusParam = showErrors ? '&status=failed' : '';
      const { data } = await api.get(`/api/v1/monitor/logs?limit=100${categoryParam}${statusParam}`);
      setLogs(data.logs || []);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const { data } = await api.get('/api/v1/monitor/stats');
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  // Initial fetch and auto-refresh
  useEffect(() => {
    if (showMonitor) {
      setIsLoading(true);
      Promise.all([fetchLogs(), fetchStats()]).finally(() => setIsLoading(false));

      if (autoRefresh) {
        const interval = setInterval(() => {
          fetchLogs();
          fetchStats();
        }, 5000); // Refresh every 5 seconds

        return () => clearInterval(interval);
      }
    }
  }, [showMonitor, filter, showErrors, autoRefresh]);

  // Auto-scroll to top (newest entries are at top)
  useEffect(() => {
    if (autoRefresh) {
      logsStartRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoRefresh]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <AnimatePresence>
      {showMonitor && (
        <motion.div
          initial={{ y: '100%', opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: '100%', opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed left-4 right-4 bottom-4 h-80 z-50"
        >
          <div className="h-full glass rounded-2xl flex flex-col overflow-hidden border border-white/10">
            {/* Header */}
            <div className="px-4 py-2 border-b border-white/10 flex items-center justify-between bg-black/30">
              <div className="flex items-center gap-3">
                <span className="text-lg">📊</span>
                <h3 className="font-semibold text-white">Darwin Monitor</h3>

                {/* Quick Stats */}
                {stats && (
                  <div className="flex items-center gap-3 ml-4 text-xs">
                    <span className="text-green-400">✅ {stats.successful}</span>
                    <span className="text-red-400">❌ {stats.failed}</span>
                    <span className="text-yellow-400">⚠️ {stats.errors_last_hour}/hr</span>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                {/* Auto-refresh toggle */}
                <button
                  onClick={() => setAutoRefresh(!autoRefresh)}
                  className={`px-2 py-1 rounded text-xs ${autoRefresh ? 'bg-green-600' : 'bg-gray-600'}`}
                  title={autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
                >
                  {autoRefresh ? '🔄' : '⏸️'}
                </button>

                {/* Filter dropdown */}
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="bg-gray-800 border border-white/10 rounded px-2 py-1 text-xs text-white"
                >
                  <option value="all">All Categories</option>
                  <option value="moltbook">🦞 Moltbook</option>
                  <option value="internet">🌐 Internet</option>
                  <option value="thinking">🧠 Thinking</option>
                  <option value="creating">🛠️ Creating</option>
                  <option value="executing">⚡ Executing</option>
                  <option value="system">⚙️ System</option>
                </select>

                {/* Errors toggle */}
                <button
                  onClick={() => setShowErrors(!showErrors)}
                  className={`px-2 py-1 rounded text-xs ${showErrors ? 'bg-red-600' : 'bg-gray-600'}`}
                >
                  {showErrors ? '❌ Errors Only' : '📋 All'}
                </button>

                {/* Close button */}
                <button
                  onClick={toggleMonitor}
                  className="p-1 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <span className="text-gray-400">✕</span>
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex flex-1 overflow-hidden">
              {/* Activity Log */}
              <div className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-xs">
                {isLoading ? (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    Loading...
                  </div>
                ) : logs.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    No activity logs yet
                  </div>
                ) : (
                  <>
                    <div ref={logsStartRef} />
                    {[...logs].reverse().map((log) => (
                      <motion.div
                        key={log.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`flex items-start gap-2 p-1.5 rounded border ${
                          log.status === 'failed'
                            ? 'border-red-500/30 bg-red-500/10'
                            : categoryColors[log.category] || 'border-gray-500/30'
                        }`}
                      >
                      <span className="text-gray-500 whitespace-nowrap">
                        {formatTime(log.timestamp)}
                      </span>
                      <span>{categoryIcons[log.category] || '📌'}</span>
                      <span>{statusIcons[log.status] || '•'}</span>
                      <span className="text-cyan-300 font-medium">[{log.action}]</span>
                      <span className="text-gray-300 flex-1 truncate" title={log.description}>
                        {log.description}
                      </span>
                      {log.duration_ms && (
                        <span className="text-gray-500 whitespace-nowrap">
                          {formatDuration(log.duration_ms)}
                        </span>
                      )}
                      {log.error && (
                        <span className="text-red-400 truncate max-w-xs" title={log.error}>
                          {log.error.slice(0, 50)}
                        </span>
                      )}
                      </motion.div>
                    ))}
                  </>
                )}
              </div>

              {/* Stats Sidebar */}
              <div className="w-48 border-l border-white/10 p-3 overflow-y-auto">
                <h4 className="text-xs font-semibold text-gray-400 mb-2">STATISTICS</h4>

                {stats && (
                  <div className="space-y-3">
                    {/* Category breakdown */}
                    <div className="space-y-1">
                      {Object.entries(stats.by_category).map(([cat, count]) => (
                        <div key={cat} className="flex items-center justify-between text-xs">
                          <span className="flex items-center gap-1">
                            {categoryIcons[cat] || '•'}
                            <span className="capitalize">{cat}</span>
                          </span>
                          <span className="text-gray-400">{count}</span>
                        </div>
                      ))}
                    </div>

                    {/* Moltbook stats */}
                    {stats.moltbook && (
                      <div className="pt-2 border-t border-white/10">
                        <h5 className="text-xs font-semibold text-orange-400 mb-1">🦞 Moltbook</h5>
                        <div className="space-y-0.5 text-xs text-gray-400">
                          <div className="flex justify-between">
                            <span>Posts Read</span>
                            <span>{stats.moltbook.posts_read}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Posts Created</span>
                            <span>{stats.moltbook.posts_created}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Comments</span>
                            <span>{stats.moltbook.comments_made}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Upvotes</span>
                            <span>{stats.moltbook.upvotes_given}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Total stats */}
                    <div className="pt-2 border-t border-white/10 text-xs">
                      <div className="flex justify-between text-gray-400">
                        <span>Total</span>
                        <span>{stats.total_activities}</span>
                      </div>
                      <div className="flex justify-between text-green-400">
                        <span>Success Rate</span>
                        <span>
                          {stats.total_activities > 0
                            ? ((stats.successful / stats.total_activities) * 100).toFixed(0)
                            : 0}
                          %
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default MonitorPanel;
