import { useState, useEffect } from 'react';
import { API_BASE } from '../utils/config';

export default function BugReportModal({ isOpen, onClose }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [counts, setCounts] = useState({});
  const [filter, setFilter] = useState('all');
  const [selectedReport, setSelectedReport] = useState(null);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState('medium');
  const [category, setCategory] = useState('general');
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchReports();
    }
  }, [isOpen, filter]);

  const fetchReports = async () => {
    try {
      setLoading(true);
      let url = `${API_BASE}/api/v1/bugreports`;
      if (filter !== 'all') {
        url += `?status=${filter}`;
      }
      const res = await fetch(url);
      const data = await res.json();
      setReports(data.reports || []);
      setCounts(data.counts || {});
    } catch (error) {
      console.error('Error fetching bug reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;

    try {
      setSubmitting(true);
      const res = await fetch(`${API_BASE}/api/v1/bugreports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), description: description.trim(), severity, category })
      });
      if (res.ok) {
        setTitle('');
        setDescription('');
        setSeverity('medium');
        setCategory('general');
        setShowForm(false);
        fetchReports();
      }
    } catch (error) {
      console.error('Error creating bug report:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (reportId, newStatus) => {
    try {
      await fetch(`${API_BASE}/api/v1/bugreports/${reportId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      setReports(reports.map(r =>
        r.id === reportId ? { ...r, status: newStatus, updated_at: new Date().toISOString() } : r
      ));
      if (selectedReport?.id === reportId) {
        setSelectedReport({ ...selectedReport, status: newStatus, updated_at: new Date().toISOString() });
      }
      fetchReports();
    } catch (error) {
      console.error('Error updating status:', error);
    }
  };

  const handleDelete = async (reportId) => {
    try {
      await fetch(`${API_BASE}/api/v1/bugreports/${reportId}`, { method: 'DELETE' });
      setReports(reports.filter(r => r.id !== reportId));
      if (selectedReport?.id === reportId) {
        setSelectedReport(null);
      }
      fetchReports();
    } catch (error) {
      console.error('Error deleting bug report:', error);
    }
  };

  const getSeverityBadge = (sev) => {
    const badges = {
      low: { label: 'Low', color: 'bg-slate-600' },
      medium: { label: 'Medium', color: 'bg-blue-600' },
      high: { label: 'High', color: 'bg-orange-600' },
      critical: { label: 'Critical', color: 'bg-red-600' }
    };
    const b = badges[sev] || badges.medium;
    return <span className={`px-2 py-0.5 rounded text-xs font-semibold text-white ${b.color}`}>{b.label}</span>;
  };

  const getStatusBadge = (st) => {
    const badges = {
      open: { label: 'Open', color: 'bg-red-500/20 text-red-300 border-red-500/50' },
      in_progress: { label: 'In Progress', color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50' },
      resolved: { label: 'Resolved', color: 'bg-green-500/20 text-green-300 border-green-500/50' },
      closed: { label: 'Closed', color: 'bg-slate-500/20 text-slate-400 border-slate-500/50' }
    };
    const b = badges[st] || badges.open;
    return <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${b.color}`}>{b.label}</span>;
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('pt-PT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  const totalOpen = (counts.open || 0) + (counts.in_progress || 0);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-lg w-full max-w-6xl h-[90vh] overflow-hidden flex flex-col border border-slate-700">
        {/* Header */}
        <div className="bg-gradient-to-r from-red-600 to-orange-600 p-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-3xl">&#128027;</span>
            <div>
              <h2 className="text-2xl font-bold text-white">Bug Reports</h2>
              <p className="text-base text-red-100">
                {totalOpen} aberto{totalOpen !== 1 ? 's' : ''} &middot; {(counts.resolved || 0) + (counts.closed || 0)} resolvidos
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowForm(!showForm)}
              className="text-sm text-white bg-white/20 hover:bg-white/30 px-3 py-1 rounded-lg transition-colors font-semibold"
            >
              + Novo Report
            </button>
            <button
              onClick={onClose}
              className="text-white text-2xl hover:bg-white/20 rounded-lg px-3 py-1 transition-colors"
            >
              &#10005;
            </button>
          </div>
        </div>

        {/* New Report Form (collapsible) */}
        {showForm && (
          <div className="bg-slate-800 border-b border-slate-700 p-4 flex-shrink-0">
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Bug title..."
                  className="flex-1 bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600 focus:border-red-500 focus:outline-none text-sm"
                  required
                />
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600 text-sm"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600 text-sm"
                >
                  <option value="general">General</option>
                  <option value="frontend">Frontend</option>
                  <option value="backend">Backend</option>
                  <option value="consciousness">Consciousness</option>
                  <option value="integration">Integration</option>
                </select>
              </div>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the bug..."
                rows={3}
                className="w-full bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600 focus:border-red-500 focus:outline-none text-sm resize-none"
                required
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting || !title.trim() || !description.trim()}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 hover:bg-red-700 text-white transition-colors disabled:opacity-50"
                >
                  {submitting ? 'A criar...' : 'Criar Report'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Filter Bar */}
        <div className="bg-slate-800 border-b border-slate-700 p-3 flex gap-2 flex-shrink-0">
          {[
            { key: 'all', label: 'Todos' },
            { key: 'open', label: 'Open' },
            { key: 'in_progress', label: 'In Progress' },
            { key: 'resolved', label: 'Resolved' },
            { key: 'closed', label: 'Closed' }
          ].map(f => (
            <button
              key={f.key}
              onClick={() => { setFilter(f.key); setSelectedReport(null); }}
              className={`px-3 py-1 rounded-lg text-sm font-semibold transition-colors ${
                filter === f.key ? 'bg-red-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {f.label}
              {f.key !== 'all' && counts[f.key] ? ` (${counts[f.key]})` : ''}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Left: List */}
          <div className="w-1/3 border-r border-slate-700 overflow-y-auto p-4 space-y-2">
            {loading ? (
              <div className="text-center text-slate-400 py-12">
                <div className="text-4xl mb-3">&#9203;</div>
                <p className="text-lg">A carregar...</p>
              </div>
            ) : reports.length === 0 ? (
              <div className="text-center text-slate-400 py-12">
                <div className="text-5xl mb-4">&#10024;</div>
                <p className="text-lg">Sem bugs reportados</p>
                <p className="text-sm mt-2">Clica "+ Novo Report" para criar</p>
              </div>
            ) : (
              reports.map((report) => (
                <div
                  key={report.id}
                  onClick={() => setSelectedReport(report)}
                  className={`p-3 rounded-lg cursor-pointer transition-all border-l-4 ${
                    selectedReport?.id === report.id
                      ? 'border-red-500 bg-red-900/20 border-2 border-red-500'
                      : report.severity === 'critical'
                        ? 'border-red-500 bg-red-900/10 hover:bg-red-900/20'
                        : report.severity === 'high'
                          ? 'border-orange-500 bg-orange-900/10 hover:bg-orange-900/20'
                          : 'border-slate-600 bg-slate-800 hover:bg-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="font-bold text-white text-sm truncate flex-1">
                      #{report.id} {report.title}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {getSeverityBadge(report.severity)}
                    {getStatusBadge(report.status)}
                    <span className="text-xs text-slate-500 capitalize">{report.category}</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {formatDate(report.created_at)}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Right: Details */}
          <div className="flex-1 overflow-y-auto p-6">
            {!selectedReport ? (
              <div className="text-center text-slate-400 py-20">
                <div className="text-6xl mb-4">&#128072;</div>
                <p className="text-xl">Seleciona um report para ver detalhes</p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Title */}
                <div>
                  <h3 className="text-2xl font-bold text-white mb-2">
                    #{selectedReport.id} {selectedReport.title}
                  </h3>
                  <div className="flex gap-3 flex-wrap">
                    {getSeverityBadge(selectedReport.severity)}
                    {getStatusBadge(selectedReport.status)}
                    <span className="px-3 py-1 rounded-full bg-slate-700 text-slate-300 text-sm capitalize">
                      {selectedReport.category}
                    </span>
                  </div>
                </div>

                {/* Description */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="text-base font-semibold text-slate-300 mb-2">Descri&ccedil;&atilde;o:</div>
                  <p className="text-base text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {selectedReport.description}
                  </p>
                </div>

                {/* Timestamps */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-slate-400">Criado:</span>
                      <span className="text-white ml-2">{formatDate(selectedReport.created_at)}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Atualizado:</span>
                      <span className="text-white ml-2">{formatDate(selectedReport.updated_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Status Actions */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="text-base font-semibold text-slate-300 mb-3">Alterar Estado:</div>
                  <div className="flex gap-2 flex-wrap">
                    {selectedReport.status !== 'open' && (
                      <button
                        onClick={() => handleStatusChange(selectedReport.id, 'open')}
                        className="px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 hover:bg-red-700 text-white transition-colors"
                      >
                        Reabrir
                      </button>
                    )}
                    {selectedReport.status !== 'in_progress' && selectedReport.status !== 'closed' && (
                      <button
                        onClick={() => handleStatusChange(selectedReport.id, 'in_progress')}
                        className="px-4 py-2 rounded-lg text-sm font-semibold bg-yellow-600 hover:bg-yellow-700 text-white transition-colors"
                      >
                        Em Progresso
                      </button>
                    )}
                    {selectedReport.status !== 'resolved' && selectedReport.status !== 'closed' && (
                      <button
                        onClick={() => handleStatusChange(selectedReport.id, 'resolved')}
                        className="px-4 py-2 rounded-lg text-sm font-semibold bg-green-600 hover:bg-green-700 text-white transition-colors"
                      >
                        Resolvido
                      </button>
                    )}
                    {selectedReport.status !== 'closed' && (
                      <button
                        onClick={() => handleStatusChange(selectedReport.id, 'closed')}
                        className="px-4 py-2 rounded-lg text-sm font-semibold bg-slate-600 hover:bg-slate-700 text-white transition-colors"
                      >
                        Fechar
                      </button>
                    )}
                  </div>
                </div>

                {/* Delete */}
                <div className="flex justify-end pt-4">
                  <button
                    onClick={() => handleDelete(selectedReport.id)}
                    className="px-4 py-2 rounded-lg text-sm bg-red-900/30 border border-red-700/50 text-red-400 hover:bg-red-900/50 transition-colors"
                  >
                    Eliminar Report
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="bg-slate-800 border-t border-slate-700 p-3 flex justify-between items-center flex-shrink-0">
          <div className="flex gap-4 text-sm text-slate-400">
            <span>Total: {Object.values(counts).reduce((a, b) => a + b, 0) || reports.length}</span>
          </div>
          <button
            onClick={onClose}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm transition-colors font-semibold"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
