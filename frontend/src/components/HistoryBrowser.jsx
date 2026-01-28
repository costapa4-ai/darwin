import { useState, useEffect } from 'react';
import { API_BASE } from '../utils/config';

export default function HistoryBrowser() {
  const [history, setHistory] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(false);
  const [selectedChange, setSelectedChange] = useState(null);

  const API_URL = API_BASE;

  useEffect(() => {
    fetchHistory();
  }, [filter]);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const url = filter === 'all'
        ? `${API_URL}/api/v1/auto-correction/history?limit=20`
        : `${API_URL}/api/v1/auto-correction/history?status=${filter}&limit=20`;

      const response = await fetch(url);
      const data = await response.json();
      setHistory(data.history || []);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    } finally {
      setLoading(false);
    }
  };

  const rollbackChange = async (rollbackId) => {
    if (!confirm('Are you sure you want to rollback this change?')) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/auto-correction/rollback/${rollbackId}`, {
        method: 'POST'
      });

      const data = await response.json();

      if (data.success) {
        alert(`✅ ${data.message}`);
        fetchHistory(); // Refresh
      } else {
        alert(`❌ ${data.message}`);
      }
    } catch (error) {
      alert(`❌ Rollback failed: ${error.message}`);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      auto_approved: { color: 'bg-blue-900/30 text-blue-400 border-blue-500/30', icon: '🤖', label: 'Auto-Approved' },
      approved: { color: 'bg-green-900/30 text-green-400 border-green-500/30', icon: '✅', label: 'Approved' },
      rejected: { color: 'bg-red-900/30 text-red-400 border-red-500/30', icon: '❌', label: 'Rejected' },
      applied: { color: 'bg-purple-900/30 text-purple-400 border-purple-500/30', icon: '✨', label: 'Applied' },
      failed: { color: 'bg-orange-900/30 text-orange-400 border-orange-500/30', icon: '⚠️', label: 'Failed' },
      rolled_back: { color: 'bg-gray-900/30 text-gray-400 border-gray-500/30', icon: '⏪', label: 'Rolled Back' },
      pending: { color: 'bg-yellow-900/30 text-yellow-400 border-yellow-500/30', icon: '⏳', label: 'Pending' }
    };

    const badge = badges[status] || badges.pending;

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs ${badge.color}`}>
        <span>{badge.icon}</span>
        <span>{badge.label}</span>
      </span>
    );
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-purple-400 flex items-center gap-2">
            <span className="text-3xl">📜</span>
            Change History
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            View past changes and rollbacks
          </p>
        </div>

        {/* Filter */}
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="bg-slate-700 text-white px-4 py-2 rounded-lg border border-slate-600"
        >
          <option value="all">All Status</option>
          <option value="auto_approved">Auto-Approved</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="applied">Applied</option>
          <option value="failed">Failed</option>
          <option value="rolled_back">Rolled Back</option>
        </select>
      </div>

      {/* History List */}
      {loading ? (
        <div className="text-center py-12">
          <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <div className="text-slate-400">Loading history...</div>
        </div>
      ) : history.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <div className="text-4xl mb-2">📭</div>
          <div>No history found</div>
        </div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {history.map((change) => (
            <div
              key={change.id}
              className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30 hover:bg-slate-700/50 transition-all cursor-pointer"
              onClick={() => setSelectedChange(selectedChange?.id === change.id ? null : change)}
            >
              {/* Header Row */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="font-medium text-white">
                    {change.generated_code?.insight_title || 'Untitled Change'}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {change.generated_code?.file_path}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {getStatusBadge(change.status)}
                  <div className="text-xs text-slate-500">
                    {formatDate(change.created_at)}
                  </div>
                </div>
              </div>

              {/* Expanded Details */}
              {selectedChange?.id === change.id && (
                <div className="mt-3 pt-3 border-t border-slate-600/30 space-y-2">
                  {/* Explanation */}
                  {change.generated_code?.explanation && (
                    <div className="text-sm text-slate-300">
                      <span className="text-slate-500">Explanation: </span>
                      {change.generated_code.explanation}
                    </div>
                  )}

                  {/* Risk & Time */}
                  <div className="flex gap-4 text-xs">
                    <div>
                      <span className="text-slate-500">Risk: </span>
                      <span className="text-slate-300">{change.generated_code?.risk_level}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Est. Time: </span>
                      <span className="text-slate-300">~{change.generated_code?.estimated_time_minutes}min</span>
                    </div>
                  </div>

                  {/* Validation Score */}
                  {change.validation && (
                    <div className="text-xs">
                      <span className="text-slate-500">Validation Score: </span>
                      <span className={`font-semibold ${
                        change.validation.score >= 80 ? 'text-green-400' :
                        change.validation.score >= 60 ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {change.validation.score}/100
                      </span>
                    </div>
                  )}

                  {/* Review Comment */}
                  {change.reviewer_comment && (
                    <div className="text-xs">
                      <span className="text-slate-500">Comment: </span>
                      <span className="text-slate-300 italic">"{change.reviewer_comment}"</span>
                    </div>
                  )}

                  {/* Dates */}
                  <div className="flex gap-4 text-xs text-slate-500">
                    {change.reviewed_at && (
                      <div>Reviewed: {formatDate(change.reviewed_at)}</div>
                    )}
                    {change.applied_at && (
                      <div>Applied: {formatDate(change.applied_at)}</div>
                    )}
                  </div>

                  {/* Rollback Button */}
                  {change.status === 'applied' && change.rollback_id && (
                    <div className="mt-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          rollbackChange(change.rollback_id);
                        }}
                        className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm font-medium rounded transition-colors"
                      >
                        ⏪ Rollback This Change
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
