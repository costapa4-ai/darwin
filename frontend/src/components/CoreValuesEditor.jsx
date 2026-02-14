import { useState, useEffect } from 'react';
import { API_BASE } from '../utils/config';

export default function CoreValuesEditor({ onBack }) {
  const [coreValues, setCoreValues] = useState([]);
  const [selfModel, setSelfModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editIndex, setEditIndex] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [newValue, setNewValue] = useState('');

  useEffect(() => {
    fetchCoreValues();
    fetchSelfModel();
  }, []);

  const fetchCoreValues = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/identity/core-values`);
      const data = await res.json();
      setCoreValues(data.core_values || []);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch core values:', err);
      setLoading(false);
    }
  };

  const fetchSelfModel = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/identity/self-model`);
      const data = await res.json();
      setSelfModel(data);
    } catch (err) {
      console.error('Failed to fetch self model:', err);
    }
  };

  const saveValues = async (values) => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/identity/core-values`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ core_values: values })
      });
      const data = await res.json();
      if (data.success) {
        setCoreValues(data.new_values);
      } else {
        alert('Failed to save: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Save error: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (index) => {
    setEditIndex(index);
    setEditValue(coreValues[index]);
  };

  const handleSaveEdit = () => {
    if (!editValue.trim()) return;
    const updated = [...coreValues];
    updated[editIndex] = editValue.trim();
    saveValues(updated);
    setEditIndex(null);
    setEditValue('');
  };

  const handleDelete = (index) => {
    if (!confirm(`Remove "${coreValues[index]}"?`)) return;
    const updated = coreValues.filter((_, i) => i !== index);
    saveValues(updated);
  };

  const handleAdd = () => {
    if (!newValue.trim()) return;
    const updated = [...coreValues, newValue.trim()];
    saveValues(updated);
    setNewValue('');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 animate-pulse text-lg">Loading identity...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Nav Bar */}
      <nav className="bg-gray-900/80 backdrop-blur border-b border-gray-800 px-6 py-3 flex items-center gap-4 sticky top-0 z-50">
        <button onClick={onBack} className="text-gray-400 hover:text-white transition">
          ← Back
        </button>
        <span className="text-lg font-semibold">🔮 Core Values & Identity</span>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Core Values */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-1">
            Core Values
          </h2>
          <p className="text-xs text-gray-600 mb-5">
            Darwin's boundaries. Only you can change these. Darwin knows them but cannot modify them.
          </p>

          <div className="space-y-3">
            {coreValues.map((value, i) => (
              <div key={i} className="flex items-center gap-3 group">
                <span className="w-6 text-gray-600 text-sm text-right">{i + 1}.</span>
                {editIndex === i ? (
                  <div className="flex-1 flex gap-2">
                    <input
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit()}
                      className="flex-1 bg-gray-800 border border-indigo-500 rounded px-3 py-2 text-sm text-white focus:outline-none"
                      autoFocus
                    />
                    <button
                      onClick={handleSaveEdit}
                      className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-sm transition"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditIndex(null)}
                      className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm transition"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="flex-1 text-gray-200 text-sm">{value}</span>
                    <button
                      onClick={() => handleEdit(i)}
                      className="opacity-0 group-hover:opacity-100 px-2 py-1 text-xs text-gray-500 hover:text-white bg-gray-800 rounded transition"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(i)}
                      className="opacity-0 group-hover:opacity-100 px-2 py-1 text-xs text-red-500 hover:text-red-300 bg-gray-800 rounded transition"
                    >
                      Remove
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>

          {/* Add new value */}
          <div className="mt-4 flex gap-2">
            <input
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              placeholder="Add a new core value..."
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
            />
            <button
              onClick={handleAdd}
              disabled={!newValue.trim() || saving}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded text-sm font-medium transition disabled:opacity-50"
            >
              + Add
            </button>
          </div>
        </div>

        {/* Self Model (read-only) */}
        {selfModel && (
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-6">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-1">
              Darwin's Self-Model
            </h2>
            <p className="text-xs text-gray-600 mb-4">
              How Darwin sees himself. Built from conversations and experiences. Read-only view.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Interests */}
              {selfModel.interests && selfModel.interests.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-gray-500 uppercase mb-2">Interests</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {selfModel.interests.map((interest, i) => (
                      <span key={i} className="px-2 py-1 bg-indigo-900/30 border border-indigo-800/50 rounded text-xs text-indigo-300">
                        {typeof interest === 'string' ? interest : interest.topic || JSON.stringify(interest)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Opinions */}
              {selfModel.opinions && selfModel.opinions.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-gray-500 uppercase mb-2">Opinions</h3>
                  <div className="space-y-1">
                    {selfModel.opinions.slice(0, 8).map((op, i) => (
                      <div key={i} className="text-xs text-gray-400">
                        {typeof op === 'string' ? op : op.opinion || JSON.stringify(op)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Milestones */}
              {selfModel.milestones && selfModel.milestones.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-gray-500 uppercase mb-2">Milestones</h3>
                  <div className="space-y-1">
                    {selfModel.milestones.slice(0, 8).map((m, i) => (
                      <div key={i} className="text-xs text-gray-400">
                        {typeof m === 'string' ? m : m.description || JSON.stringify(m)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Personality Notes */}
              {selfModel.personality_notes && selfModel.personality_notes.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-gray-500 uppercase mb-2">Personality Notes</h3>
                  <div className="space-y-1">
                    {selfModel.personality_notes.slice(0, 8).map((n, i) => (
                      <div key={i} className="text-xs text-gray-400">
                        {typeof n === 'string' ? n : JSON.stringify(n)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
