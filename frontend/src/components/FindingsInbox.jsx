import { useState, useEffect } from 'react';
import { API_BASE } from '../utils/config';

export default function FindingsInbox({ isOpen, onClose }) {
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [filter, setFilter] = useState('all'); // all, unread, by type
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchFindings();
      fetchStats();
    }
  }, [isOpen, filter]);

  const fetchFindings = async () => {
    try {
      setLoading(true);
      let url = `${API_BASE}/api/v1/findings`;

      if (filter === 'unread') {
        url = `${API_BASE}/api/v1/findings/unread`;
      } else if (filter !== 'all') {
        url = `${API_BASE}/api/v1/findings?type=${filter}`;
      }

      const res = await fetch(url);
      const data = await res.json();
      setFindings(data.findings || []);
    } catch (error) {
      console.error('Error fetching findings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/findings/statistics`);
      const data = await res.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleMarkRead = async (findingId) => {
    try {
      await fetch(`${API_BASE}/api/v1/findings/${findingId}/read`, {
        method: 'POST'
      });
      // Update local state
      setFindings(findings.map(f =>
        f.id === findingId ? { ...f, viewed_at: new Date().toISOString() } : f
      ));
      fetchStats();
    } catch (error) {
      console.error('Error marking finding as read:', error);
    }
  };

  const handleDismiss = async (findingId) => {
    try {
      await fetch(`${API_BASE}/api/v1/findings/${findingId}/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Dismissed via UI' })
      });
      // Remove from list
      setFindings(findings.filter(f => f.id !== findingId));
      setSelectedFinding(null);
      fetchStats();
    } catch (error) {
      console.error('Error dismissing finding:', error);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await fetch(`${API_BASE}/api/v1/findings/mark-all-read`, {
        method: 'POST'
      });
      // Update local state
      setFindings(findings.map(f => ({ ...f, viewed_at: new Date().toISOString() })));
      fetchStats();
    } catch (error) {
      console.error('Error marking all as read:', error);
    }
  };

  const getTypeIcon = (type) => {
    const icons = {
      'discovery': '🔍',
      'insight': '💡',
      'anomaly': '⚠️',
      'suggestion': '💭',
      'curiosity': '🤔'
    };
    return icons[type] || '📌';
  };

  const getTypeColor = (type) => {
    const colors = {
      'discovery': 'border-blue-500 bg-blue-900/20',
      'insight': 'border-green-500 bg-green-900/20',
      'anomaly': 'border-red-500 bg-red-900/20',
      'suggestion': 'border-purple-500 bg-purple-900/20',
      'curiosity': 'border-yellow-500 bg-yellow-900/20'
    };
    return colors[type] || 'border-slate-500 bg-slate-800';
  };

  const getPriorityBadge = (priority) => {
    const badges = {
      '1': { label: 'Low', color: 'bg-slate-600' },
      '2': { label: 'Medium', color: 'bg-blue-600' },
      '3': { label: 'High', color: 'bg-orange-600' },
      '4': { label: 'Urgent', color: 'bg-red-600' },
      'low': { label: 'Low', color: 'bg-slate-600' },
      'medium': { label: 'Medium', color: 'bg-blue-600' },
      'high': { label: 'High', color: 'bg-orange-600' },
      'urgent': { label: 'Urgent', color: 'bg-red-600' }
    };
    const badge = badges[priority] || badges['2'];
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-semibold text-white ${badge.color}`}>
        {badge.label}
      </span>
    );
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('pt-PT', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-lg w-full max-w-6xl h-[90vh] overflow-hidden flex flex-col border border-slate-700">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-3xl">📬</span>
            <div>
              <h2 className="text-2xl font-bold text-white">Findings Inbox</h2>
              <p className="text-base text-purple-100">
                {stats?.total_unread || 0} não lidos de {stats?.total_active || 0} ativos
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleMarkAllRead}
              className="text-sm text-white bg-white/20 hover:bg-white/30 px-3 py-1 rounded-lg transition-colors"
            >
              ✓ Marcar todos lidos
            </button>
            <button
              onClick={onClose}
              className="text-white text-2xl hover:bg-white/20 rounded-lg px-3 py-1 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="bg-slate-800 border-b border-slate-700 p-3 flex gap-2 flex-shrink-0">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1 rounded-lg text-sm font-semibold transition-colors ${
              filter === 'all' ? 'bg-purple-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => setFilter('unread')}
            className={`px-3 py-1 rounded-lg text-sm font-semibold transition-colors ${
              filter === 'unread' ? 'bg-purple-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Não Lidos
          </button>
          <span className="border-l border-slate-600 mx-2"></span>
          <button
            onClick={() => setFilter('discovery')}
            className={`px-3 py-1 rounded-lg text-sm transition-colors flex items-center gap-1 ${
              filter === 'discovery' ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            🔍 Descobertas
          </button>
          <button
            onClick={() => setFilter('insight')}
            className={`px-3 py-1 rounded-lg text-sm transition-colors flex items-center gap-1 ${
              filter === 'insight' ? 'bg-green-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            💡 Insights
          </button>
          <button
            onClick={() => setFilter('anomaly')}
            className={`px-3 py-1 rounded-lg text-sm transition-colors flex items-center gap-1 ${
              filter === 'anomaly' ? 'bg-red-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            ⚠️ Anomalias
          </button>
          <button
            onClick={() => setFilter('suggestion')}
            className={`px-3 py-1 rounded-lg text-sm transition-colors flex items-center gap-1 ${
              filter === 'suggestion' ? 'bg-purple-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            💭 Sugestões
          </button>
          <button
            onClick={() => setFilter('curiosity')}
            className={`px-3 py-1 rounded-lg text-sm transition-colors flex items-center gap-1 ${
              filter === 'curiosity' ? 'bg-yellow-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            🤔 Curiosidades
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Left: List of findings */}
          <div className="w-1/3 border-r border-slate-700 overflow-y-auto p-4 space-y-2">
            {loading ? (
              <div className="text-center text-slate-400 py-12">
                <div className="text-4xl mb-3">⏳</div>
                <p className="text-lg">A carregar...</p>
              </div>
            ) : findings.length === 0 ? (
              <div className="text-center text-slate-400 py-12">
                <div className="text-5xl mb-4">📭</div>
                <p className="text-lg">Nenhum finding encontrado</p>
                <p className="text-sm mt-2">Darwin está a explorar...</p>
              </div>
            ) : (
              findings.map((finding) => (
                <div
                  key={finding.id}
                  onClick={() => {
                    setSelectedFinding(finding);
                    if (!finding.viewed_at) {
                      handleMarkRead(finding.id);
                    }
                  }}
                  className={`p-3 rounded-lg cursor-pointer transition-all border-l-4 ${
                    selectedFinding?.id === finding.id
                      ? `${getTypeColor(finding.type)} border-2 border-purple-500`
                      : `${getTypeColor(finding.type)} hover:brightness-110`
                  } ${!finding.viewed_at ? 'ring-2 ring-purple-500/50' : ''}`}
                >
                  <div className="flex items-start gap-2 mb-1">
                    <span className="text-xl flex-shrink-0">{getTypeIcon(finding.type)}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-bold text-white text-sm truncate ${
                          !finding.viewed_at ? 'text-purple-200' : ''
                        }`}>
                          {finding.title}
                        </span>
                        {!finding.viewed_at && (
                          <span className="w-2 h-2 bg-purple-500 rounded-full flex-shrink-0"></span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {getPriorityBadge(finding.priority)}
                        <span className="text-xs text-slate-400 truncate">
                          {finding.source}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {formatDate(finding.created_at)}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Right: Finding details */}
          <div className="flex-1 overflow-y-auto p-6">
            {!selectedFinding ? (
              <div className="text-center text-slate-400 py-20">
                <div className="text-6xl mb-4">👈</div>
                <p className="text-xl">Seleciona um finding para ver detalhes</p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Title */}
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-4xl">{getTypeIcon(selectedFinding.type)}</span>
                    <h3 className="text-2xl font-bold text-white">
                      {selectedFinding.title}
                    </h3>
                  </div>
                  <div className="flex gap-3 text-base">
                    {getPriorityBadge(selectedFinding.priority)}
                    <span className="px-3 py-1 rounded-full bg-slate-700 text-slate-300 text-sm capitalize">
                      {selectedFinding.type}
                    </span>
                    <span className="px-3 py-1 rounded-full bg-slate-700 text-slate-300 text-sm">
                      {selectedFinding.source}
                    </span>
                  </div>
                </div>

                {/* Description */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="text-base font-semibold text-slate-300 mb-2">📝 Descrição:</div>
                  <p className="text-base text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {selectedFinding.description}
                  </p>
                </div>

                {/* Impact - What this means */}
                {selectedFinding.impact && (
                  <div className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border border-amber-700/50 rounded-lg p-4">
                    <div className="text-base font-semibold text-amber-300 mb-2">💡 O Que Isto Significa:</div>
                    <p className="text-base text-amber-100 leading-relaxed">
                      {selectedFinding.impact}
                    </p>
                  </div>
                )}

                {/* Recommended Actions */}
                {selectedFinding.recommended_actions && selectedFinding.recommended_actions.length > 0 && (
                  <div className="bg-gradient-to-r from-blue-900/30 to-cyan-900/30 border border-blue-700/50 rounded-lg p-4">
                    <div className="text-base font-semibold text-blue-300 mb-3">🎯 Ações Recomendadas:</div>
                    <ul className="space-y-2">
                      {selectedFinding.recommended_actions.map((action, idx) => (
                        <li key={idx} className="flex items-start gap-3 text-blue-100">
                          <span className="text-blue-400 font-bold mt-0.5">→</span>
                          <span className="text-base">{action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Resolution Steps - How to resolve */}
                {selectedFinding.resolution_steps && selectedFinding.resolution_steps.length > 0 && (
                  <div className="bg-gradient-to-r from-green-900/30 to-emerald-900/30 border border-green-700/50 rounded-lg p-4">
                    <div className="text-base font-semibold text-green-300 mb-3">🔧 Como Resolver:</div>
                    <ol className="space-y-2">
                      {selectedFinding.resolution_steps.map((step, idx) => (
                        <li key={idx} className="flex items-start gap-3 text-green-100">
                          <span className="bg-green-600 text-white text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                            {idx + 1}
                          </span>
                          <span className="text-base">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Web Solutions - AI-Searched Resources */}
                {selectedFinding.metadata?.web_solutions && selectedFinding.metadata.web_solutions.length > 0 && (
                  <div className="bg-gradient-to-r from-indigo-900/30 to-violet-900/30 border border-indigo-700/50 rounded-lg p-4">
                    <div className="text-base font-semibold text-indigo-300 mb-3">🌐 Soluções da Internet (Pesquisa Automática):</div>
                    <div className="space-y-3">
                      {selectedFinding.metadata.web_solutions.map((solution, idx) => (
                        <div key={idx} className="bg-slate-800/50 rounded-lg p-3 hover:bg-slate-700/50 transition-colors">
                          <a
                            href={solution.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block"
                          >
                            <div className="text-indigo-300 font-medium hover:text-indigo-200 transition-colors flex items-center gap-2">
                              <span>🔗</span>
                              <span className="truncate">{solution.title}</span>
                              <span className="text-xs text-slate-500">↗</span>
                            </div>
                            {solution.snippet && (
                              <p className="text-sm text-slate-400 mt-1 line-clamp-2">
                                {solution.snippet}
                              </p>
                            )}
                          </a>
                        </div>
                      ))}
                    </div>
                    {selectedFinding.metadata?.diagnostic_info?.web_search_query && (
                      <div className="mt-3 text-xs text-slate-500 flex items-center gap-1">
                        <span>🔍 Pesquisa:</span>
                        <code className="bg-slate-700/50 px-2 py-0.5 rounded">
                          {selectedFinding.metadata.diagnostic_info.web_search_query}
                        </code>
                      </div>
                    )}
                  </div>
                )}

                {/* Related Files */}
                {selectedFinding.related_files && selectedFinding.related_files.length > 0 && (
                  <div className="bg-slate-800 rounded-lg p-4">
                    <div className="text-base font-semibold text-slate-300 mb-2">📁 Ficheiros Relacionados:</div>
                    <div className="space-y-1">
                      {selectedFinding.related_files.map((file, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <span className="text-slate-400">📄</span>
                          <code className="text-sm text-cyan-400 bg-slate-700/50 px-2 py-1 rounded font-mono">
                            {file}
                          </code>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Learn More */}
                {selectedFinding.learn_more && (
                  <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                    <div className="text-base font-semibold text-slate-300 mb-2">📚 Mais Informação:</div>
                    <p className="text-sm text-slate-400 leading-relaxed">
                      {selectedFinding.learn_more}
                    </p>
                  </div>
                )}

                {/* Category Badge */}
                {selectedFinding.category && (
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 text-sm">Categoria:</span>
                    <span className="px-3 py-1 rounded-full bg-purple-600/30 border border-purple-500/50 text-purple-300 text-sm">
                      {selectedFinding.category}
                    </span>
                  </div>
                )}

                {/* Metadata - Collapsed by default */}
                {selectedFinding.metadata && Object.keys(selectedFinding.metadata).length > 0 && (
                  <details className="bg-slate-800 rounded-lg">
                    <summary className="p-4 cursor-pointer text-base font-semibold text-slate-300 hover:bg-slate-700/50 rounded-lg transition-colors">
                      📊 Detalhes Técnicos ({Object.keys(selectedFinding.metadata).length} campos)
                    </summary>
                    <div className="p-4 pt-0 space-y-2">
                      {Object.entries(selectedFinding.metadata).map(([key, value]) => (
                        <div key={key} className="flex items-start gap-2">
                          <span className="text-sm text-slate-400 font-mono min-w-32">
                            {key}:
                          </span>
                          <span className="text-sm text-slate-300 break-all">
                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}

                {/* Timestamps */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="text-base font-semibold text-slate-300 mb-2">🕐 Timestamps:</div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-slate-400">Criado:</span>
                      <span className="text-white ml-2">{formatDate(selectedFinding.created_at)}</span>
                    </div>
                    {selectedFinding.viewed_at && (
                      <div>
                        <span className="text-slate-400">Visto:</span>
                        <span className="text-white ml-2">{formatDate(selectedFinding.viewed_at)}</span>
                      </div>
                    )}
                    {selectedFinding.expires_at && (
                      <div>
                        <span className="text-slate-400">Expira:</span>
                        <span className="text-white ml-2">{formatDate(selectedFinding.expires_at)}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex gap-4 pt-4">
                  {!selectedFinding.viewed_at && (
                    <button
                      onClick={() => handleMarkRead(selectedFinding.id)}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-6 py-4 rounded-lg text-lg font-bold transition-colors"
                    >
                      ✓ Marcar Lido
                    </button>
                  )}
                  <button
                    onClick={() => handleDismiss(selectedFinding.id)}
                    className="flex-1 bg-slate-700 hover:bg-slate-600 text-white px-6 py-4 rounded-lg text-lg font-bold transition-colors"
                  >
                    🗑️ Dispensar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Stats */}
        {stats && (
          <div className="bg-slate-800 border-t border-slate-700 p-3 flex justify-between items-center flex-shrink-0">
            <div className="flex gap-4 text-sm text-slate-400">
              <span>📊 Por tipo: {Object.entries(stats.by_type || {}).map(([t, c]) => `${t}(${c})`).join(', ')}</span>
            </div>
            <button
              onClick={onClose}
              className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm transition-colors font-semibold"
            >
              Fechar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
