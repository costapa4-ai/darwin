import { useState, useEffect, useRef } from 'react';
import { API_BASE } from '../utils/config';

const categoryIcons = {
  moltbook: '🦞',
  internet: '🌐',
  thinking: '🧠',
  creating: '🛠️',
  executing: '⚡',
  system: '⚙️',
  consciousness: '🌊',
  memory: '💾',
};

const categoryColors = {
  moltbook: 'text-orange-400 border-orange-500/30 bg-orange-900/20',
  internet: 'text-blue-400 border-blue-500/30 bg-blue-900/20',
  thinking: 'text-purple-400 border-purple-500/30 bg-purple-900/20',
  creating: 'text-green-400 border-green-500/30 bg-green-900/20',
  executing: 'text-yellow-400 border-yellow-500/30 bg-yellow-900/20',
  system: 'text-gray-400 border-gray-500/30 bg-gray-900/20',
  consciousness: 'text-cyan-400 border-cyan-500/30 bg-cyan-900/20',
  memory: 'text-teal-400 border-teal-500/30 bg-teal-900/20',
};

const statusIcons = {
  success: '✅',
  failed: '❌',
  started: '🔄',
  partial: '⚠️',
};

export default function MonitorPanel({ isOpen, onClose }) {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('all');
  const [showErrors, setShowErrors] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const logsEndRef = useRef(null);

  // Fetch logs
  const fetchLogs = async () => {
    try {
      const categoryParam = filter !== 'all' ? `&category=${filter}` : '';
      const statusParam = showErrors ? '&status=failed' : '';
      const res = await fetch(`${API_BASE}/api/v1/monitor/logs?limit=100${categoryParam}${statusParam}`);
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/monitor/stats`);
      const data = await res.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  // Initial fetch and auto-refresh
  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      Promise.all([fetchLogs(), fetchStats()]).finally(() => setIsLoading(false));

      if (autoRefresh) {
        const interval = setInterval(() => {
          fetchLogs();
          fetchStats();
        }, 5000);

        return () => clearInterval(interval);
      }
    }
  }, [isOpen, filter, showErrors, autoRefresh]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoRefresh && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoRefresh]);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDuration = (ms) => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-end justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-t-lg shadow-2xl border border-slate-700 w-full max-w-6xl h-96 flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-emerald-600 px-4 py-2 rounded-t-lg flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg">📊</span>
            <h3 className="font-semibold text-white">Darwin Monitor</h3>

            {/* Quick Stats */}
            {stats && (
              <div className="flex items-center gap-3 ml-4 text-xs">
                <span className="text-green-200">✅ {stats.successful}</span>
                <span className="text-red-200">❌ {stats.failed}</span>
                <span className="text-yellow-200">⚠️ {stats.errors_last_hour}/hr</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Auto-refresh toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-2 py-1 rounded text-xs ${autoRefresh ? 'bg-green-700' : 'bg-gray-600'}`}
              title={autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
            >
              {autoRefresh ? '🔄' : '⏸️'}
            </button>

            {/* Filter dropdown */}
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="bg-slate-800 border border-white/10 rounded px-2 py-1 text-xs text-white"
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
              onClick={onClose}
              className="text-white hover:bg-white/20 rounded-lg px-3 py-1 text-xl transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Activity Log */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-xs">
            {isLoading ? (
              <div className="flex items-center justify-center h-full text-slate-500">
                Loading...
              </div>
            ) : logs.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-500">
                No activity logs yet
              </div>
            ) : (
              logs.map((log, idx) => (
                <div
                  key={log.id || idx}
                  className={`flex items-start gap-2 p-1.5 rounded border ${
                    log.status === 'failed'
                      ? 'border-red-500/30 bg-red-900/20'
                      : categoryColors[log.category] || 'border-slate-500/30 bg-slate-800'
                  }`}
                >
                  <span className="text-slate-500 whitespace-nowrap">
                    {formatTime(log.timestamp)}
                  </span>
                  <span>{categoryIcons[log.category] || '📌'}</span>
                  <span>{statusIcons[log.status] || '•'}</span>
                  <span className="text-cyan-300 font-medium">[{log.action}]</span>
                  <span className="text-slate-300 flex-1 truncate" title={log.description}>
                    {log.description}
                  </span>
                  {log.duration_ms && (
                    <span className="text-slate-500 whitespace-nowrap">
                      {formatDuration(log.duration_ms)}
                    </span>
                  )}
                  {log.error && (
                    <span className="text-red-400 truncate max-w-xs" title={log.error}>
                      {log.error.slice(0, 50)}
                    </span>
                  )}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>

          {/* Stats Sidebar */}
          <div className="w-48 border-l border-slate-700 p-3 overflow-y-auto bg-slate-800/50">
            <h4 className="text-xs font-semibold text-slate-400 mb-2">STATISTICS</h4>

            {stats && (
              <div className="space-y-3">
                {/* Category breakdown */}
                <div className="space-y-1">
                  {Object.entries(stats.by_category || {}).map(([cat, count]) => (
                    <div key={cat} className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1">
                        {categoryIcons[cat] || '•'}
                        <span className="capitalize">{cat}</span>
                      </span>
                      <span className="text-slate-400">{count}</span>
                    </div>
                  ))}
                </div>

                {/* Moltbook stats */}
                {stats.moltbook && (
                  <div className="pt-2 border-t border-slate-700">
                    <h5 className="text-xs font-semibold text-orange-400 mb-1">🦞 Moltbook</h5>
                    <div className="space-y-0.5 text-xs text-slate-400">
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
                <div className="pt-2 border-t border-slate-700 text-xs">
                  <div className="flex justify-between text-slate-400">
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
    </div>
  );
}
