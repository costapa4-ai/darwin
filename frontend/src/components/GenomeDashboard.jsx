import { useState, useEffect } from 'react';
import { API_BASE } from '../utils/config';

const DOMAIN_META = {
  emotions:    { icon: '🧠', label: 'Emotions',    color: 'from-rose-500 to-pink-600' },
  actions:     { icon: '💪', label: 'Actions',      color: 'from-amber-500 to-orange-600' },
  rhythms:     { icon: '⏰', label: 'Rhythms',      color: 'from-blue-500 to-cyan-600' },
  personality: { icon: '🎭', label: 'Personality',  color: 'from-purple-500 to-violet-600' },
  cognition:   { icon: '🧩', label: 'Cognition',    color: 'from-emerald-500 to-teal-600' },
  social:      { icon: '💬', label: 'Social',       color: 'from-sky-500 to-blue-600' },
  creativity:  { icon: '✨', label: 'Creativity',   color: 'from-fuchsia-500 to-pink-600' },
};

export default function GenomeDashboard({ onBack }) {
  const [genomeStatus, setGenomeStatus] = useState(null);
  const [selectedDomain, setSelectedDomain] = useState(null);
  const [domainData, setDomainData] = useState(null);
  const [changelog, setChangelog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rolling, setRolling] = useState(false);

  useEffect(() => {
    fetchGenomeStatus();
    fetchChangelog();
    const interval = setInterval(fetchGenomeStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchGenomeStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/genome/status`);
      const data = await res.json();
      setGenomeStatus(data);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch genome status:', err);
      setLoading(false);
    }
  };

  const fetchChangelog = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/genome/history?limit=30`);
      const data = await res.json();
      setChangelog(data.changelog || []);
    } catch (err) {
      console.error('Failed to fetch changelog:', err);
    }
  };

  const fetchDomain = async (name) => {
    setSelectedDomain(name);
    try {
      const res = await fetch(`${API_BASE}/api/v1/genome/domain/${name}`);
      const data = await res.json();
      setDomainData(data.data);
    } catch (err) {
      console.error('Failed to fetch domain:', err);
    }
  };

  const handleRollback = async () => {
    if (!confirm('This will rollback to the last genome snapshot. Continue?')) return;
    setRolling(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/genome/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message);
        fetchGenomeStatus();
        fetchChangelog();
      } else {
        alert('Rollback failed: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Rollback error: ' + err.message);
    } finally {
      setRolling(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 animate-pulse text-lg">Loading genome...</div>
      </div>
    );
  }

  const stats = genomeStatus?.stats || {};
  const perDomain = stats.per_domain || {};

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Nav Bar */}
      <nav className="bg-gray-900/80 backdrop-blur border-b border-gray-800 px-6 py-3 flex items-center gap-4 sticky top-0 z-50">
        <button onClick={onBack} className="text-gray-400 hover:text-white transition">
          ← Back
        </button>
        <span className="text-lg font-semibold">🧬 Genome Dashboard</span>
        <div className="flex-1" />
        <button
          onClick={handleRollback}
          disabled={rolling}
          className="px-3 py-1.5 bg-red-900/50 hover:bg-red-800/60 border border-red-700/50 rounded text-red-300 text-sm transition disabled:opacity-50"
        >
          {rolling ? 'Rolling back...' : '↩ Manual Rollback'}
        </button>
      </nav>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Status Banner */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Version</div>
              <div className="text-2xl font-bold text-white">v{genomeStatus?.version || 1}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Total Mutations</div>
              <div className="text-2xl font-bold text-amber-400">{stats.total_mutations || 0}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Kept / Rolled</div>
              <div className="text-2xl font-bold">
                <span className="text-green-400">{stats.kept_mutations || 0}</span>
                <span className="text-gray-600 mx-1">/</span>
                <span className="text-red-400">{stats.rolledback_mutations || 0}</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Evolution</div>
              <div className="text-lg font-bold">
                {genomeStatus?.can_evolve ? (
                  <span className="text-green-400">READY</span>
                ) : (
                  <span className="text-yellow-400">
                    {genomeStatus?.cycles_since_last_mutation || 0}/{genomeStatus?.mutation_cooldown_cycles || 10} cycles
                  </span>
                )}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Rollback</div>
              <div className="text-lg font-bold">
                {genomeStatus?.rollback_available ? (
                  <span className="text-green-400">Available</span>
                ) : (
                  <span className="text-red-400">Locked</span>
                )}
              </div>
            </div>
          </div>
          {genomeStatus?.last_mutation_at && (
            <div className="mt-3 text-xs text-gray-500">
              Last mutation: {new Date(genomeStatus.last_mutation_at).toLocaleString()}
            </div>
          )}
        </div>

        {/* Domain Cards */}
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Brain Domains</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {Object.entries(DOMAIN_META).map(([key, meta]) => {
              const ds = perDomain[key] || {};
              const isSelected = selectedDomain === key;
              return (
                <button
                  key={key}
                  onClick={() => fetchDomain(key)}
                  className={`p-4 rounded-xl border transition-all text-left ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-950/40 ring-1 ring-indigo-500/30'
                      : 'border-gray-800 bg-gray-900/40 hover:border-gray-700 hover:bg-gray-900/60'
                  }`}
                >
                  <div className="text-2xl mb-1">{meta.icon}</div>
                  <div className="text-sm font-medium text-gray-200">{meta.label}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {ds.mutations || 0}m / {ds.kept || 0}k / {ds.rolledback || 0}r
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Domain Detail */}
        {selectedDomain && domainData && (
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              {DOMAIN_META[selectedDomain]?.icon} {DOMAIN_META[selectedDomain]?.label} Domain
            </h3>
            <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-xs text-gray-300 overflow-auto max-h-96 font-mono">
              {JSON.stringify(domainData, null, 2)}
            </pre>
          </div>
        )}

        {/* Evolution Log */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Evolution Log ({changelog.length} entries)
          </h3>
          {changelog.length === 0 ? (
            <div className="text-gray-600 text-sm py-4 text-center">
              No mutations yet. Darwin is ready to evolve when the sleep "evolve" mode is selected.
            </div>
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {changelog.slice().reverse().map((entry, i) => (
                <div key={i} className="flex items-start gap-3 text-sm border-b border-gray-800/50 pb-2">
                  <span className="text-xs text-gray-600 w-32 shrink-0">
                    {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '?'}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                    entry.status === 'rolledback' ? 'bg-red-900/40 text-red-400' : 'bg-green-900/40 text-green-400'
                  }`}>
                    {entry.status || 'applied'}
                  </span>
                  <span className="text-gray-400 font-mono text-xs">{entry.key}</span>
                  <span className="text-gray-600">→</span>
                  <span className="text-gray-300 text-xs truncate">{JSON.stringify(entry.new_value)}</span>
                  <span className="text-gray-600 text-xs truncate flex-1">{entry.reason}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
