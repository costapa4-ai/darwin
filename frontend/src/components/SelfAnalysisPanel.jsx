import { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { API_BASE } from '../utils/config';

export default function SelfAnalysisPanel() {
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [insights, setInsights] = useState([]);
  const [filter, setFilter] = useState('all');
  const [selectedComponent, setSelectedComponent] = useState('all');

  const analyzeSystem = async () => {
    setLoading(true);
    try {
      const API_URL = API_BASE;
      const response = await fetch(`${API_URL}/api/v1/introspection/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deep_analysis: true, include_metrics: true })
      });

      if (!response.ok) throw new Error('Analysis failed');

      const data = await response.json();
      setAnalysis(data.analysis);

      // Fetch insights
      await fetchInsights();
    } catch (error) {
      console.error('Failed to analyze:', error);
      alert('Failed to analyze: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchInsights = async (priority = null, component = null) => {
    try {
      const API_URL = API_BASE;
      let url = `${API_URL}/api/v1/introspection/insights?limit=100`;
      if (priority && priority !== 'all') url += `&priority=${priority}`;
      if (component && component !== 'all') url += `&component=${component}`;

      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch insights');

      const data = await response.json();
      setInsights(data.insights || []);
    } catch (error) {
      console.error('Failed to fetch insights:', error);
    }
  };

  useEffect(() => {
    if (filter !== 'all' || selectedComponent !== 'all') {
      fetchInsights(filter, selectedComponent);
    }
  }, [filter, selectedComponent]);

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'text-red-400 bg-red-900/30 border-red-500/30';
      case 'medium': return 'text-yellow-400 bg-yellow-900/30 border-yellow-500/30';
      case 'low': return 'text-blue-400 bg-blue-900/30 border-blue-500/30';
      default: return 'text-gray-400 bg-gray-900/30 border-gray-500/30';
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'optimization': return '⚡';
      case 'feature': return '✨';
      case 'improvement': return '📈';
      case 'refactor': return '🔧';
      default: return '💡';
    }
  };

  const getComponentIcon = (component) => {
    switch (component) {
      case 'backend': return '🐍';
      case 'frontend': return '⚛️';
      case 'docker': return '🐳';
      case 'sandbox': return '📦';
      default: return '🔹';
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-purple-400 flex items-center gap-2">
            <span className="text-3xl">🔮</span>
            Self-Analysis
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Darwin analyzing itself for improvements
          </p>
        </div>

        <button
          onClick={analyzeSystem}
          disabled={loading}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            loading
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
              : 'bg-purple-600 hover:bg-purple-700 text-white'
          }`}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              Analyzing...
            </span>
          ) : (
            '🔍 Run Analysis'
          )}
        </button>
      </div>

      {/* Filters */}
      {insights.length > 0 && (
        <div className="flex gap-4 mb-6">
          {/* Priority Filter */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-slate-700 text-white px-4 py-2 rounded-lg border border-slate-600"
          >
            <option value="all">All Priorities</option>
            <option value="high">🔴 High Priority</option>
            <option value="medium">🟡 Medium Priority</option>
            <option value="low">🔵 Low Priority</option>
          </select>

          {/* Component Filter */}
          <select
            value={selectedComponent}
            onChange={(e) => setSelectedComponent(e.target.value)}
            className="bg-slate-700 text-white px-4 py-2 rounded-lg border border-slate-600"
          >
            <option value="all">All Components</option>
            <option value="backend">🐍 Backend</option>
            <option value="frontend">⚛️ Frontend</option>
            <option value="docker">🐳 Docker</option>
            <option value="sandbox">📦 Sandbox</option>
          </select>
        </div>
      )}

      {/* Summary Cards */}
      {analysis?.summary && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
            <div className="text-3xl font-bold text-purple-400">
              {analysis.summary.total_insights}
            </div>
            <div className="text-sm text-slate-400">Total Insights</div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
            <div className="text-3xl font-bold text-red-400">
              {analysis.summary.high_priority_count}
            </div>
            <div className="text-sm text-slate-400">High Priority</div>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
            <div className="text-3xl font-bold text-blue-400">
              {analysis.metrics?.codebase?.total_lines_of_code || 0}
            </div>
            <div className="text-sm text-slate-400">Lines of Code</div>
          </div>
        </div>
      )}

      {/* Insights List */}
      {insights.length > 0 ? (
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
          {insights.map((insight, idx) => (
            <div
              key={idx}
              className={`rounded-lg p-4 border ${getPriorityColor(insight.priority)} transition-all hover:scale-[1.01]`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{getTypeIcon(insight.type)}</span>
                  <span className="text-2xl">{getComponentIcon(insight.component)}</span>
                  <h3 className="font-bold text-white text-lg">{insight.title}</h3>
                </div>

                <div className="flex gap-2">
                  <span className={`text-xs px-2 py-1 rounded border ${getPriorityColor(insight.priority)}`}>
                    {insight.priority.toUpperCase()}
                  </span>
                  <span className="text-xs px-2 py-1 rounded border border-slate-500 bg-slate-700/50 text-slate-300">
                    {insight.type}
                  </span>
                </div>
              </div>

              {/* Description */}
              <p className="text-sm text-slate-300 mb-3">{insight.description}</p>

              {/* Current vs Proposed */}
              <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
                <div className="bg-slate-900/50 rounded p-2">
                  <div className="text-xs text-slate-500 mb-1">Current:</div>
                  <div className="text-slate-300">{insight.current_state}</div>
                </div>
                <div className="bg-slate-900/50 rounded p-2">
                  <div className="text-xs text-slate-500 mb-1">Proposed:</div>
                  <div className="text-green-300">{insight.proposed_change}</div>
                </div>
              </div>

              {/* Benefits */}
              {insight.benefits && insight.benefits.length > 0 && (
                <div className="mb-2">
                  <div className="text-xs text-slate-500 mb-1">Benefits:</div>
                  <ul className="text-sm text-slate-300 space-y-1">
                    {insight.benefits.map((benefit, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span>{benefit}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Impact & Location */}
              <div className="flex items-center justify-between text-xs text-slate-500 mt-2">
                <span>Impact: <span className="text-slate-300">{insight.estimated_impact}</span></span>
                {insight.code_location && (
                  <span className="font-mono bg-slate-900/50 px-2 py-1 rounded">
                    {insight.code_location}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">🔮</div>
          <div className="text-lg text-slate-400 mb-2">No analysis yet</div>
          <div className="text-sm text-slate-500">
            Click "Run Analysis" to let Darwin analyze itself
          </div>
        </div>
      )}

      {/* Footer Info */}
      {analysis?.summary?.recommended_next_steps && (
        <div className="mt-6 bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
          <div className="font-semibold text-purple-300 mb-2">
            🎯 Recommended Next Steps:
          </div>
          <ul className="space-y-1 text-sm text-slate-300">
            {analysis.summary.recommended_next_steps.map((step, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-purple-400">{i + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
