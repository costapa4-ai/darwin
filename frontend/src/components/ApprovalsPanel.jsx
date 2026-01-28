import { useState, useEffect } from 'react';
import { API_BASE } from '../utils/config';

export default function ApprovalsPanel({ isOpen, onClose }) {
  const [pendingChanges, setPendingChanges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedChange, setSelectedChange] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchPendingChanges();
    }
  }, [isOpen]);

  const fetchPendingChanges = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/v1/consciousness/approvals/pending`);
      const data = await res.json();
      setPendingChanges(data.pending_changes || []);
    } catch (error) {
      console.error('Error fetching pending changes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (changeId) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/consciousness/approvals/${changeId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment: 'Aprovado via interface' })
      });

      if (res.ok) {
        // Remove from list
        setPendingChanges(pendingChanges.filter(c => c.id !== changeId));
        setSelectedChange(null);
        alert('✅ Mudança aprovada com sucesso!');
      }
    } catch (error) {
      console.error('Error approving change:', error);
      alert('❌ Erro ao aprovar mudança');
    }
  };

  const handleReject = async (changeId) => {
    const reason = prompt('Razão para rejeitar:');
    if (!reason) return;

    try {
      const res = await fetch(`${API_BASE}/api/v1/consciousness/approvals/${changeId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });

      if (res.ok) {
        // Remove from list
        setPendingChanges(pendingChanges.filter(c => c.id !== changeId));
        setSelectedChange(null);
        alert('❌ Mudança rejeitada');
      }
    } catch (error) {
      console.error('Error rejecting change:', error);
      alert('❌ Erro ao rejeitar mudança');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-lg w-full max-w-6xl h-[90vh] overflow-hidden flex flex-col border border-slate-700">
        {/* Header */}
        <div className="bg-gradient-to-r from-yellow-600 to-orange-600 p-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-3xl">⚠️</span>
            <div>
              <h2 className="text-2xl font-bold text-white">Mudanças Pendentes</h2>
              <p className="text-base text-yellow-100">{pendingChanges.length} ideias aguardam aprovação</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white text-2xl hover:bg-white/20 rounded-lg px-3 py-1 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Left: List of changes */}
          <div className="w-1/3 border-r border-slate-700 overflow-y-auto p-5 space-y-3">
            {loading ? (
              <div className="text-center text-slate-400 py-12">
                <div className="text-4xl mb-3">⏳</div>
                <p className="text-lg">A carregar...</p>
              </div>
            ) : pendingChanges.length === 0 ? (
              <div className="text-center text-slate-400 py-12">
                <div className="text-5xl mb-4">✅</div>
                <p className="text-lg">Nenhuma mudança pendente!</p>
              </div>
            ) : (
              pendingChanges.map((change) => (
                <div
                  key={change.id}
                  onClick={() => setSelectedChange(change)}
                  className={`p-4 rounded-lg cursor-pointer transition-all ${
                    selectedChange?.id === change.id
                      ? 'bg-yellow-900/50 border-2 border-yellow-500'
                      : 'bg-slate-800 border-2 border-slate-700 hover:border-yellow-600'
                  }`}
                >
                  <div className="flex items-start gap-3 mb-2">
                    <span className="text-2xl">
                      {change.generated_code.risk_level === 'low' ? '🟢' :
                       change.generated_code.risk_level === 'medium' ? '🟡' : '🔴'}
                    </span>
                    <div className="flex-1">
                      <div className="font-bold text-white text-base mb-1">
                        {change.generated_code.insight_title}
                      </div>
                      <div className="text-sm text-slate-400">
                        Risco: {change.generated_code.risk_level}
                      </div>
                      <div className="text-sm text-slate-400">
                        Score: {change.validation.score}/100
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-slate-500 font-mono">
                    {change.id}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Right: Change details */}
          <div className="flex-1 overflow-y-auto p-6">
            {!selectedChange ? (
              <div className="text-center text-slate-400 py-20">
                <div className="text-6xl mb-4">👈</div>
                <p className="text-xl">Seleciona uma mudança para ver detalhes</p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Title */}
                <div>
                  <h3 className="text-2xl font-bold text-white mb-2">
                    {selectedChange.generated_code.insight_title}
                  </h3>
                  <div className="flex gap-3 text-base">
                    <span className={`px-3 py-1 rounded-full font-semibold ${
                      selectedChange.generated_code.risk_level === 'low' ? 'bg-green-900/30 text-green-300' :
                      selectedChange.generated_code.risk_level === 'medium' ? 'bg-yellow-900/30 text-yellow-300' :
                      'bg-red-900/30 text-red-300'
                    }`}>
                      Risco: {selectedChange.generated_code.risk_level}
                    </span>
                    <span className="px-3 py-1 rounded-full bg-blue-900/30 text-blue-300 font-semibold">
                      Score: {selectedChange.validation.score}/100
                    </span>
                  </div>
                </div>

                {/* Explanation */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="text-base font-semibold text-slate-300 mb-2">📝 Explicação:</div>
                  <p className="text-base text-slate-400 leading-relaxed">
                    {selectedChange.generated_code.explanation}
                  </p>
                </div>

                {/* File */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="text-base font-semibold text-slate-300 mb-2">📄 Ficheiro:</div>
                  <code className="text-base text-blue-400 font-mono">
                    {selectedChange.generated_code.file_path}
                  </code>
                </div>

                {/* Diff */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="text-base font-semibold text-slate-300 mb-3">🔄 Alterações:</div>
                  <pre className="bg-slate-950 rounded p-4 overflow-x-auto text-sm font-mono text-slate-300 leading-relaxed max-h-96 overflow-y-auto">
                    {selectedChange.generated_code.diff_unified || 'Sem diff disponível'}
                  </pre>
                </div>

                {/* Validation warnings */}
                {selectedChange.validation.warnings && selectedChange.validation.warnings.length > 0 && (
                  <div className="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-4">
                    <div className="text-base font-semibold text-yellow-300 mb-2">⚠️ Avisos:</div>
                    <ul className="space-y-1">
                      {selectedChange.validation.warnings.map((warning, i) => (
                        <li key={i} className="text-base text-yellow-200">• {warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex gap-4 pt-4">
                  <button
                    onClick={() => handleApprove(selectedChange.id)}
                    className="flex-1 bg-green-600 hover:bg-green-700 text-white px-6 py-4 rounded-lg text-lg font-bold transition-colors"
                  >
                    ✅ Aprovar
                  </button>
                  <button
                    onClick={() => handleReject(selectedChange.id)}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white px-6 py-4 rounded-lg text-lg font-bold transition-colors"
                  >
                    ❌ Rejeitar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
