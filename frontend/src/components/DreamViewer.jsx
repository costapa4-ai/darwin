import { useState, useEffect } from 'react';
import DreamVisualizer from './DreamVisualizer';

export default function DreamViewer() {
  const [dreamStatus, setDreamStatus] = useState(null);
  const [dreamHistory, setDreamHistory] = useState([]);
  const [selectedDream, setSelectedDream] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Fetch current dream status every 5 seconds
  useEffect(() => {
    const fetchDreamStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/phase3/dreams/status`);
        if (!response.ok) return;
        const data = await response.json();
        setDreamStatus(data);
      } catch (error) {
        console.error('Failed to fetch dream status:', error);
      }
    };

    fetchDreamStatus();
    const interval = setInterval(fetchDreamStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch dream history
  const fetchDreamHistory = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/phase3/dreams/history?limit=20`);
      if (!response.ok) throw new Error('Failed to fetch history');
      const data = await response.json();
      setDreamHistory(data.dreams || []);
    } catch (error) {
      console.error('Failed to fetch dream history:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch detailed dream info
  const fetchDreamDetails = async (dreamId) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/phase3/dreams/history/${dreamId}`);
      if (!response.ok) throw new Error('Failed to fetch dream details');
      const data = await response.json();
      setSelectedDream(data);
    } catch (error) {
      console.error('Failed to fetch dream details:', error);
    }
  };

  const getDreamIcon = (type) => {
    const icons = {
      'algorithm_exploration': '🔍',
      'pattern_discovery': '🧩',
      'optimization_experiment': '⚡',
      'hypothesis_testing': '🧪',
      'creative_coding': '🎨',
      'library_learning': '📚',
      'self_analysis': '🔬'
    };
    return icons[type] || '💭';
  };

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const currentlyDreaming = dreamStatus?.currently_dreaming;
  const currentDream = dreamStatus?.current_dream;

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-purple-400 flex items-center gap-2">
            <span className="text-3xl">💭</span>
            Dream Viewer
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            See what Darwin is exploring autonomously
          </p>
        </div>

        <button
          onClick={() => {
            setShowHistory(!showHistory);
            if (!showHistory) fetchDreamHistory();
          }}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
        >
          {showHistory ? '🔮 Current Dream' : '📜 History'}
        </button>
      </div>

      {/* Current Dream View */}
      {!showHistory && (
        <div>
          {currentlyDreaming && currentDream ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Side: Dream Visualization */}
              <div className="flex items-center justify-center">
                <DreamVisualizer dreamStatus={dreamStatus} currentDream={currentDream} />
              </div>

              {/* Right Side: Dream Details */}
              <div className="space-y-4">
              {/* Dream Header */}
              <div className="bg-gradient-to-r from-purple-900/40 to-blue-900/40 rounded-lg p-6 border border-purple-500/30">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-5xl">{getDreamIcon(currentDream.type)}</span>
                    <div>
                      <h3 className="text-xl font-bold text-white">
                        {currentDream.type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                      </h3>
                      <p className="text-slate-300 text-sm mt-1">{currentDream.description}</p>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-3xl font-bold text-purple-400">
                      {Math.floor(currentDream.duration_minutes)}m
                    </div>
                    <div className="text-xs text-slate-400">dreaming</div>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>Progress</span>
                    <span>{currentDream.progress}%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${currentDream.progress}%` }}
                    ></div>
                  </div>
                </div>

                {/* Hypothesis (if exists) */}
                {currentDream.hypothesis && (
                  <div className="bg-blue-900/30 border border-blue-500/30 rounded-lg p-3 mb-4">
                    <div className="text-xs text-blue-400 font-semibold mb-1">🧪 HYPOTHESIS</div>
                    <div className="text-sm text-slate-200">{currentDream.hypothesis}</div>
                  </div>
                )}

                {/* Results (if exists) */}
                {currentDream.results && (
                  <div className="bg-green-900/30 border border-green-500/30 rounded-lg p-3 mb-4">
                    <div className="text-xs text-green-400 font-semibold mb-1">📊 RESULTS</div>
                    <pre className="text-sm text-slate-200 overflow-auto">
                      {JSON.stringify(currentDream.results, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              {/* Insights in Real-Time */}
              <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-bold text-white flex items-center gap-2">
                    <span>💡</span>
                    Insights Discovered
                    <span className="text-purple-400">({currentDream.insights_count})</span>
                  </h4>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="text-xs text-slate-400">Live</span>
                  </div>
                </div>

                {currentDream.insights && currentDream.insights.length > 0 ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {currentDream.insights.map((insight, idx) => (
                      <div
                        key={idx}
                        className="bg-slate-800/50 rounded p-3 border border-slate-600 animate-fade-in"
                      >
                        <div className="flex items-start gap-2">
                          <span className="text-purple-400 font-mono text-xs mt-1">#{idx + 1}</span>
                          <span className="text-slate-200 text-sm flex-1">{insight}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-slate-400 text-sm">
                    Waiting for insights...
                  </div>
                )}
              </div>

              {/* Dream Info */}
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="bg-slate-700/30 rounded p-3 border border-slate-600">
                  <div className="text-slate-400 mb-1">Started At</div>
                  <div className="text-white font-mono">
                    {new Date(currentDream.started_at).toLocaleTimeString()}
                  </div>
                </div>
                <div className="bg-slate-700/30 rounded p-3 border border-slate-600">
                  <div className="text-slate-400 mb-1">Duration</div>
                  <div className="text-white font-mono">
                    {formatDuration(currentDream.duration_seconds)}
                  </div>
                </div>
                <div className="bg-slate-700/30 rounded p-3 border border-slate-600">
                  <div className="text-slate-400 mb-1">Dream ID</div>
                  <div className="text-white font-mono text-xs truncate">
                    {currentDream.id}
                  </div>
                </div>
              </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Side: Idle Visualization */}
              <div className="flex items-center justify-center">
                <DreamVisualizer dreamStatus={dreamStatus} currentDream={null} />
              </div>

              {/* Right Side: Idle Message */}
              <div className="flex items-center justify-center">
                <div className="text-center">
                  <div className="text-6xl mb-4">😴</div>
                  <div className="text-lg text-slate-400 mb-2">Not Currently Dreaming</div>
                  <div className="text-sm text-slate-500">
                    Darwin will start dreaming when the system is idle
                  </div>
              {dreamStatus?.idle_status && (
                <div className="mt-4 text-xs text-slate-400">
                  Idle for {Math.floor(dreamStatus.idle_status.idle_duration_minutes)} minutes
                  {dreamStatus.idle_status.should_dream && (
                    <span className="text-purple-400 ml-2">(ready to dream)</span>
                  )}
                </div>
              )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Dream History View */}
      {showHistory && (
        <div>
          {loading ? (
            <div className="text-center py-12">
              <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <div className="text-slate-400">Loading dream history...</div>
            </div>
          ) : dreamHistory.length > 0 ? (
            <div className="space-y-3">
              {dreamHistory.map((dream) => (
                <div
                  key={dream.id}
                  onClick={() => fetchDreamDetails(dream.id)}
                  className="bg-slate-700/30 rounded-lg p-4 border border-slate-600 hover:border-purple-500/50 cursor-pointer transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3 flex-1">
                      <span className="text-3xl">{getDreamIcon(dream.type)}</span>
                      <div className="flex-1">
                        <div className="font-bold text-white mb-1">
                          {dream.type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                        </div>
                        <div className="text-sm text-slate-400 mb-2">{dream.description}</div>
                        <div className="flex gap-3 text-xs text-slate-500">
                          <span>💡 {dream.insights_count} insights</span>
                          <span>⏱️ {formatDuration(dream.duration_seconds)}</span>
                          <span>📅 {new Date(dream.started_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                    <div>
                      {dream.success ? (
                        <span className="text-green-400 text-xl">✓</span>
                      ) : (
                        <span className="text-red-400 text-xl">✗</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📜</div>
              <div className="text-lg text-slate-400 mb-2">No Dream History</div>
              <div className="text-sm text-slate-500">
                Dream history will appear here once Darwin starts dreaming
              </div>
            </div>
          )}

          {/* Selected Dream Details Modal */}
          {selectedDream && (
            <div
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              onClick={() => setSelectedDream(null)}
            >
              <div
                className="bg-slate-800 rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto border border-purple-500/30"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                      <span className="text-3xl">{getDreamIcon(selectedDream.type)}</span>
                      {selectedDream.type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </h3>
                    <p className="text-sm text-slate-400 mt-1">{selectedDream.description}</p>
                  </div>
                  <button
                    onClick={() => setSelectedDream(null)}
                    className="text-slate-400 hover:text-white text-2xl"
                  >
                    ×
                  </button>
                </div>

                {selectedDream.hypothesis && (
                  <div className="bg-blue-900/30 border border-blue-500/30 rounded-lg p-3 mb-4">
                    <div className="text-xs text-blue-400 font-semibold mb-1">🧪 HYPOTHESIS</div>
                    <div className="text-sm text-slate-200">{selectedDream.hypothesis}</div>
                  </div>
                )}

                {selectedDream.results && (
                  <div className="bg-green-900/30 border border-green-500/30 rounded-lg p-3 mb-4">
                    <div className="text-xs text-green-400 font-semibold mb-1">📊 RESULTS</div>
                    <pre className="text-sm text-slate-200 overflow-auto">
                      {JSON.stringify(selectedDream.results, null, 2)}
                    </pre>
                  </div>
                )}

                <div className="mb-4">
                  <h4 className="font-bold text-white mb-2">💡 Insights ({selectedDream.insights_count})</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {selectedDream.insights.map((insight, idx) => (
                      <div key={idx} className="bg-slate-700/50 rounded p-2 text-sm text-slate-200">
                        <span className="text-purple-400 font-mono mr-2">#{idx + 1}</span>
                        {insight}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-700/30 rounded p-2">
                    <div className="text-slate-400">Duration</div>
                    <div className="text-white font-mono">{formatDuration(selectedDream.duration_seconds)}</div>
                  </div>
                  <div className="bg-slate-700/30 rounded p-2">
                    <div className="text-slate-400">Status</div>
                    <div className={selectedDream.success ? 'text-green-400' : 'text-red-400'}>
                      {selectedDream.success ? '✓ Success' : '✗ Failed'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
