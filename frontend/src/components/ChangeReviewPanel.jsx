import { useState, useEffect } from 'react';
import DiffViewer from './DiffViewer';
import ValidationDisplay from './ValidationDisplay';
import { API_BASE } from '../utils/config';

export default function ChangeReviewPanel() {
  const [pendingChanges, setPendingChanges] = useState([]);
  const [selectedChange, setSelectedChange] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const API_URL = API_BASE;

  useEffect(() => {
    fetchPendingChanges();
    // Refresh every 10 seconds
    const interval = setInterval(fetchPendingChanges, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchPendingChanges = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auto-correction/pending`);
      const data = await response.json();
      setPendingChanges(data.changes || []);
    } catch (error) {
      console.error('Failed to fetch pending changes:', error);
    }
  };

  const selectChange = async (change) => {
    setLoading(true);
    try {
      // Fetch full details
      const response = await fetch(`${API_URL}/api/v1/auto-correction/change/${change.id}`);
      const data = await response.json();
      setSelectedChange(data.change);
    } catch (error) {
      console.error('Failed to fetch change details:', error);
    } finally {
      setLoading(false);
    }
  };

  const approveChange = async (comment = '') => {
    if (!selectedChange) return;

    setActionLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/auto-correction/approve/${selectedChange.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment })
      });

      const data = await response.json();

      if (data.success) {
        setMessage({
          type: 'success',
          text: `✅ ${data.message}`,
          rollback_id: data.rollback_id
        });
        setSelectedChange(null);
        fetchPendingChanges();
      } else {
        setMessage({
          type: 'error',
          text: `❌ ${data.message}`
        });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: `❌ Failed to approve: ${error.message}`
      });
    } finally {
      setActionLoading(false);
    }
  };

  const rejectChange = async (reason) => {
    if (!selectedChange || !reason) return;

    setActionLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/auto-correction/reject/${selectedChange.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });

      const data = await response.json();

      if (data.success) {
        setMessage({
          type: 'info',
          text: data.message
        });
        setSelectedChange(null);
        fetchPendingChanges();
      } else {
        setMessage({
          type: 'error',
          text: `❌ ${data.message}`
        });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: `❌ Failed to reject: ${error.message}`
      });
    } finally {
      setActionLoading(false);
    }
  };

  const getRiskBadge = (risk) => {
    const colors = {
      low: 'bg-green-900/30 text-green-400 border-green-500/30',
      medium: 'bg-yellow-900/30 text-yellow-400 border-yellow-500/30',
      high: 'bg-red-900/30 text-red-400 border-red-500/30'
    };
    return colors[risk] || colors.medium;
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-purple-400 flex items-center gap-2">
            <span className="text-3xl">🔧</span>
            Auto-Correction Review
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Review and approve code changes suggested by Darwin
          </p>
        </div>

        <div className="text-right">
          <div className="text-2xl font-bold text-purple-400">
            {pendingChanges.length}
          </div>
          <div className="text-xs text-slate-400">Pending Changes</div>
        </div>
      </div>

      {/* Message Display */}
      {message && (
        <div className={`mb-4 p-4 rounded-lg border ${
          message.type === 'success' ? 'bg-green-900/20 border-green-500/30 text-green-400' :
          message.type === 'error' ? 'bg-red-900/20 border-red-500/30 text-red-400' :
          'bg-blue-900/20 border-blue-500/30 text-blue-400'
        }`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="font-medium">{message.text}</p>
              {message.rollback_id && (
                <p className="text-xs mt-1 opacity-75">
                  Rollback ID: {message.rollback_id}
                </p>
              )}
            </div>
            <button
              onClick={() => setMessage(null)}
              className="text-current opacity-50 hover:opacity-100"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        {/* Left: Pending Changes List */}
        <div className="col-span-1 space-y-2">
          <h3 className="font-semibold text-slate-300 mb-3">Pending Changes</h3>

          {pendingChanges.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <div className="text-4xl mb-2">✨</div>
              <div className="text-sm">No pending changes</div>
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {pendingChanges.map((change) => (
                <button
                  key={change.id}
                  onClick={() => selectChange(change)}
                  className={`w-full text-left p-3 rounded-lg border transition-all ${
                    selectedChange?.id === change.id
                      ? 'bg-purple-900/30 border-purple-500/50'
                      : 'bg-slate-700/30 border-slate-600/30 hover:bg-slate-700/50'
                  }`}
                >
                  <div className="font-medium text-sm text-white truncate">
                    {change.generated_code?.insight_title || 'Untitled Change'}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {change.generated_code?.file_path}
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`text-xs px-2 py-0.5 rounded border ${getRiskBadge(change.generated_code?.risk_level)}`}>
                      {change.generated_code?.risk_level || 'unknown'}
                    </span>
                    <span className="text-xs text-slate-500">
                      ~{change.generated_code?.estimated_time_minutes || 0}min
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Change Details */}
        <div className="col-span-2">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                <div className="text-slate-400">Loading change details...</div>
              </div>
            </div>
          ) : selectedChange ? (
            <div className="space-y-4">
              {/* Change Info */}
              <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
                <h3 className="font-semibold text-white text-lg mb-2">
                  {selectedChange.generated_code.insight_title}
                </h3>
                <p className="text-sm text-slate-300 mb-3">
                  {selectedChange.generated_code.explanation}
                </p>

                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <div className="text-xs text-slate-500">File</div>
                    <div className="text-slate-300 font-mono text-xs truncate">
                      {selectedChange.generated_code.file_path}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Risk Level</div>
                    <span className={`inline-block px-2 py-0.5 rounded border text-xs ${getRiskBadge(selectedChange.generated_code.risk_level)}`}>
                      {selectedChange.generated_code.risk_level}
                    </span>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Est. Time</div>
                    <div className="text-slate-300">
                      ~{selectedChange.generated_code.estimated_time_minutes} minutes
                    </div>
                  </div>
                </div>
              </div>

              {/* Validation Results */}
              <ValidationDisplay validation={selectedChange.validation} />

              {/* Diff Viewer */}
              <DiffViewer
                original={selectedChange.generated_code.original_code}
                modified={selectedChange.generated_code.new_code}
                filename={selectedChange.generated_code.file_path}
              />

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    const comment = prompt('Approval comment (optional):');
                    if (comment !== null) approveChange(comment);
                  }}
                  disabled={actionLoading}
                  className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  {actionLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      ✅ Approve & Apply
                    </>
                  )}
                </button>

                <button
                  onClick={() => {
                    const reason = prompt('Rejection reason (required):');
                    if (reason) rejectChange(reason);
                  }}
                  disabled={actionLoading}
                  className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  ❌ Reject
                </button>

                <button
                  onClick={() => setSelectedChange(null)}
                  className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-20 text-slate-500">
              <div className="text-center">
                <div className="text-6xl mb-3">👈</div>
                <div className="text-lg">Select a change to review</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
