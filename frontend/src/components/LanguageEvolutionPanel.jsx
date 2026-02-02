import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../utils/config';

const TOPIC_LABELS = {
  ai_consciousness: 'AI Consciousness',
  philosophy: 'Philosophy',
  technology: 'Technology',
  creativity: 'Creativity',
  learning: 'Learning',
  social: 'Social',
  emotions: 'Emotions',
};

const TOPIC_COLORS = {
  ai_consciousness: 'bg-purple-500',
  philosophy: 'bg-blue-500',
  technology: 'bg-cyan-500',
  creativity: 'bg-pink-500',
  learning: 'bg-green-500',
  social: 'bg-amber-500',
  emotions: 'bg-rose-500',
};

const CONTENT_TYPE_LABELS = {
  read: 'Thought',
  comment: 'Comment',
  share: 'Post',
};

const CONTENT_TYPE_ICONS = {
  read: '💭',
  comment: '💬',
  share: '📝',
};

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Simple SVG Line Chart
function SimpleLineChart({ data, width = 300, height = 120, lineColor = '#06b6d4', fillColor = 'rgba(6, 182, 212, 0.1)' }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-slate-500 text-sm" style={{ width, height }}>
        No data available
      </div>
    );
  }

  const values = data.map(d => d.y);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  const padding = { top: 15, right: 10, bottom: 25, left: 10 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const points = data.map((d, i) => ({
    x: padding.left + (i / (data.length - 1 || 1)) * chartWidth,
    y: padding.top + chartHeight - ((d.y - minVal) / range) * chartHeight,
    value: d.y,
    label: d.x,
  }));

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const fillD = pathD + ` L ${points[points.length - 1]?.x || 0} ${padding.top + chartHeight} L ${points[0]?.x || 0} ${padding.top + chartHeight} Z`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* Grid lines */}
      <g stroke="rgba(255,255,255,0.1)">
        {[0, 0.5, 1].map(ratio => (
          <line
            key={ratio}
            x1={padding.left}
            y1={padding.top + chartHeight * (1 - ratio)}
            x2={width - padding.right}
            y2={padding.top + chartHeight * (1 - ratio)}
            strokeDasharray="4 4"
          />
        ))}
      </g>

      {/* Fill area */}
      <path d={fillD} fill={fillColor} />

      {/* Line */}
      <path d={pathD} fill="none" stroke={lineColor} strokeWidth={2} strokeLinecap="round" />

      {/* Dots */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill={lineColor}>
          <title>{p.label}: {p.value}</title>
        </circle>
      ))}

      {/* X-axis labels */}
      <g fill="rgba(255,255,255,0.5)" fontSize={10}>
        <text x={points[0]?.x} y={height - 5} textAnchor="start">{formatDate(data[0]?.x)}</text>
        {data.length > 1 && (
          <text x={points[points.length - 1]?.x} y={height - 5} textAnchor="end">{formatDate(data[data.length - 1]?.x)}</text>
        )}
      </g>
    </svg>
  );
}

// Sentiment Gauge
function SentimentGauge({ value, size = 100 }) {
  const clampedValue = Math.max(-1, Math.min(1, value));
  const angle = ((clampedValue + 1) / 2) * 180;
  const needleAngle = angle - 90;
  const needleLength = size * 0.35;
  const centerX = size / 2;
  const centerY = size * 0.55;

  const needleX = centerX + needleLength * Math.cos((needleAngle * Math.PI) / 180);
  const needleY = centerY + needleLength * Math.sin((needleAngle * Math.PI) / 180);

  const getColor = (val) => {
    if (val < -0.3) return '#ef4444';
    if (val < 0) return '#f59e0b';
    if (val < 0.3) return '#84cc16';
    return '#22c55e';
  };

  const color = getColor(clampedValue);
  const arcRadius = size * 0.38;
  const arcWidth = size * 0.08;

  const getLabel = (val) => {
    if (val < -0.5) return 'Negative';
    if (val < -0.2) return 'Slightly Neg.';
    if (val < 0.2) return 'Neutral';
    if (val < 0.5) return 'Slightly Pos.';
    return 'Positive';
  };

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.6} viewBox={`0 0 ${size} ${size * 0.6}`}>
        <defs>
          <linearGradient id="sentimentGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="25%" stopColor="#f59e0b" />
            <stop offset="50%" stopColor="#84cc16" />
            <stop offset="100%" stopColor="#22c55e" />
          </linearGradient>
        </defs>

        {/* Background arc */}
        <path
          d={`M ${centerX - arcRadius} ${centerY} A ${arcRadius} ${arcRadius} 0 0 1 ${centerX + arcRadius} ${centerY}`}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={arcWidth}
          strokeLinecap="round"
        />

        {/* Colored arc */}
        <path
          d={`M ${centerX - arcRadius} ${centerY} A ${arcRadius} ${arcRadius} 0 0 1 ${centerX + arcRadius} ${centerY}`}
          fill="none"
          stroke="url(#sentimentGradient)"
          strokeWidth={arcWidth}
          strokeLinecap="round"
          opacity={0.5}
        />

        {/* Needle */}
        <line x1={centerX} y1={centerY} x2={needleX} y2={needleY} stroke={color} strokeWidth={3} strokeLinecap="round" />
        <circle cx={centerX} cy={centerY} r={size * 0.04} fill={color} />

        {/* Value */}
        <text x={centerX} y={centerY + size * 0.15} fontSize={12} fontWeight="bold" fill={color} textAnchor="middle">
          {clampedValue.toFixed(2)}
        </text>
      </svg>
      <span className="text-xs text-slate-400">{getLabel(clampedValue)}</span>
    </div>
  );
}

export default function LanguageEvolutionPanel({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [content, setContent] = useState([]);
  const [history, setHistory] = useState([]);
  const [vocabGrowth, setVocabGrowth] = useState([]);
  const [contentFilter, setContentFilter] = useState(null);
  const [expandedItems, setExpandedItems] = useState({});

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryRes, historyRes, vocabRes, contentRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/language-evolution/summary`),
        fetch(`${API_BASE}/api/v1/language-evolution/metrics/history?days=30`),
        fetch(`${API_BASE}/api/v1/language-evolution/vocabulary/growth?days=30`),
        fetch(`${API_BASE}/api/v1/language-evolution/content?limit=50${contentFilter ? `&type=${contentFilter}` : ''}`),
      ]);

      const [summaryData, historyData, vocabData, contentData] = await Promise.all([
        summaryRes.json(),
        historyRes.json(),
        vocabRes.json(),
        contentRes.json(),
      ]);

      setSummary(summaryData);
      setHistory(historyData);
      setVocabGrowth(vocabData);
      setContent(contentData.items || []);
    } catch (error) {
      console.error('Failed to fetch language evolution data:', error);
    } finally {
      setLoading(false);
    }
  }, [contentFilter]);

  useEffect(() => {
    if (isOpen) {
      fetchData();
    }
  }, [isOpen, fetchData]);

  if (!isOpen) return null;

  const toggleExpand = (id) => {
    setExpandedItems(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-lg shadow-2xl border border-slate-700 w-full max-w-2xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-cyan-600 to-purple-600 p-4 rounded-t-lg flex justify-between items-center flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📊</span>
            <div>
              <h2 className="text-xl font-bold text-white">Language Evolution</h2>
              <p className="text-xs text-cyan-100">Darwin's writing patterns</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white/20 rounded-lg px-3 py-1 text-xl transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700 flex-shrink-0">
          {['overview', 'timeline', 'analytics'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'text-cyan-400 border-b-2 border-cyan-400 bg-slate-800/50'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/30'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-400" />
            </div>
          ) : (
            <>
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-800 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span>📚</span>
                        <span className="text-xs text-slate-400">Vocabulary Size</span>
                      </div>
                      <span className="text-xl font-bold text-purple-400">{summary?.vocabulary_size?.toLocaleString() || 0}</span>
                    </div>
                    <div className="bg-slate-800 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span>✏️</span>
                        <span className="text-xs text-slate-400">Total Words</span>
                      </div>
                      <span className="text-xl font-bold text-cyan-400">{summary?.total_word_count?.toLocaleString() || 0}</span>
                    </div>
                    <div className="bg-slate-800 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span>📝</span>
                        <span className="text-xs text-slate-400">Today's Words</span>
                      </div>
                      <span className="text-xl font-bold text-green-400">{summary?.today?.words_written?.toLocaleString() || 0}</span>
                    </div>
                    <div className="bg-slate-800 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span>🆕</span>
                        <span className="text-xs text-slate-400">New Words Today</span>
                      </div>
                      <span className="text-xl font-bold text-amber-400">{summary?.today?.new_vocabulary || 0}</span>
                    </div>
                  </div>

                  {/* Sentiment Gauge */}
                  <div className="bg-slate-800 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-slate-300 mb-3">Recent Sentiment</h3>
                    <div className="flex justify-center">
                      <SentimentGauge value={summary?.recent_sentiment || 0} size={120} />
                    </div>
                  </div>

                  {/* Vocabulary Growth Chart */}
                  {vocabGrowth.length > 0 && (
                    <div className="bg-slate-800 rounded-lg p-4">
                      <h3 className="text-sm font-medium text-slate-300 mb-3">Vocabulary Growth</h3>
                      <SimpleLineChart
                        data={vocabGrowth.map(v => ({ x: v.date, y: v.vocabulary_size }))}
                        width={550}
                        height={100}
                        lineColor="#a855f7"
                        fillColor="rgba(168, 85, 247, 0.1)"
                      />
                    </div>
                  )}

                  {/* Top Topics */}
                  {summary?.top_topics?.length > 0 && (
                    <div className="bg-slate-800 rounded-lg p-4">
                      <h3 className="text-sm font-medium text-slate-300 mb-3">Top Topics (Last 7 Days)</h3>
                      <div className="space-y-2">
                        {summary.top_topics.slice(0, 5).map(([topic, count]) => (
                          <div key={topic} className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${TOPIC_COLORS[topic] || 'bg-slate-500'}`} />
                            <span className="text-sm text-slate-300 flex-1">{TOPIC_LABELS[topic] || topic}</span>
                            <span className="text-xs text-slate-500">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sample Vocabulary */}
                  {summary?.sample_vocabulary?.length > 0 && (
                    <div className="bg-slate-800 rounded-lg p-4">
                      <h3 className="text-sm font-medium text-slate-300 mb-3">Recent Vocabulary</h3>
                      <div className="flex flex-wrap gap-2">
                        {summary.sample_vocabulary.slice(-15).map((word, i) => (
                          <span key={i} className="px-2 py-1 text-xs bg-slate-700 rounded-full text-slate-300">
                            {word}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'timeline' && (
                <div className="space-y-4">
                  {/* Filter */}
                  <div className="flex gap-2">
                    {[null, 'read', 'comment', 'share'].map(f => (
                      <button
                        key={f || 'all'}
                        onClick={() => setContentFilter(f)}
                        className={`px-3 py-1 text-xs rounded-full transition-colors ${
                          contentFilter === f
                            ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                            : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                        }`}
                      >
                        {f ? CONTENT_TYPE_LABELS[f] : 'All'}
                      </button>
                    ))}
                  </div>

                  {/* Content List */}
                  {content.length === 0 ? (
                    <div className="text-center text-slate-400 py-8">
                      No content recorded yet. Darwin needs to interact with Moltbook.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {content.map(item => (
                        <div
                          key={item.id}
                          className="bg-slate-800 rounded-lg p-3 cursor-pointer hover:bg-slate-700/50 transition-colors"
                          onClick={() => toggleExpand(item.id)}
                        >
                          <div className="flex items-start gap-3">
                            <span className="text-xl">{CONTENT_TYPE_ICONS[item.type]}</span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-medium text-slate-400">{CONTENT_TYPE_LABELS[item.type]}</span>
                                <span className="text-xs text-slate-500">{formatTimestamp(item.timestamp)}</span>
                              </div>

                              {item.source_post_title && (
                                <p className="text-xs text-slate-500 mb-1 truncate">Re: {item.source_post_title}</p>
                              )}

                              <p className={`text-sm text-slate-200 ${expandedItems[item.id] ? '' : 'line-clamp-2'}`}>
                                {item.darwin_content}
                              </p>

                              {/* Metrics */}
                              <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                                <span>{item.metrics?.word_count || 0} words</span>
                                <span className={
                                  item.metrics?.sentiment > 0 ? 'text-green-400' :
                                  item.metrics?.sentiment < 0 ? 'text-red-400' : ''
                                }>
                                  {item.metrics?.sentiment > 0 ? '+' : ''}{item.metrics?.sentiment?.toFixed(2)} sentiment
                                </span>
                              </div>

                              {/* Topics */}
                              {item.metrics?.topics?.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {item.metrics.topics.map(topic => (
                                    <span
                                      key={topic}
                                      className={`px-2 py-0.5 text-xs rounded-full ${TOPIC_COLORS[topic] || 'bg-slate-600'} bg-opacity-20 text-slate-300`}
                                    >
                                      {TOPIC_LABELS[topic] || topic}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {/* New vocabulary */}
                              {expandedItems[item.id] && item.metrics?.vocabulary_new_words?.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-slate-700">
                                  <span className="text-xs text-slate-500">New words: </span>
                                  <span className="text-xs text-amber-400">{item.metrics.vocabulary_new_words.join(', ')}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'analytics' && (
                <div className="space-y-4">
                  {/* Vocabulary Growth */}
                  <div className="bg-slate-800 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-slate-300 mb-3">Vocabulary Growth (30 Days)</h3>
                    <SimpleLineChart
                      data={vocabGrowth.map(v => ({ x: v.date, y: v.vocabulary_size }))}
                      width={550}
                      height={120}
                      lineColor="#a855f7"
                      fillColor="rgba(168, 85, 247, 0.1)"
                    />
                  </div>

                  {/* Words per Day */}
                  <div className="bg-slate-800 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-slate-300 mb-3">Words Written (30 Days)</h3>
                    <SimpleLineChart
                      data={history.map(h => ({ x: h.date, y: h.total_words }))}
                      width={550}
                      height={120}
                      lineColor="#06b6d4"
                      fillColor="rgba(6, 182, 212, 0.1)"
                    />
                  </div>

                  {/* Sentiment Trend */}
                  <div className="bg-slate-800 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-slate-300 mb-3">Sentiment Trend (30 Days)</h3>
                    <SimpleLineChart
                      data={history.map(h => ({ x: h.date, y: h.avg_sentiment }))}
                      width={550}
                      height={120}
                      lineColor="#22c55e"
                      fillColor="rgba(34, 197, 94, 0.1)"
                    />
                  </div>

                  {/* Statistics Table */}
                  {summary && (
                    <div className="bg-slate-800 rounded-lg p-4">
                      <h3 className="text-sm font-medium text-slate-300 mb-3">Statistics</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-400">First recorded</span>
                          <span className="text-slate-200">
                            {summary.first_content_date ? new Date(summary.first_content_date).toLocaleDateString() : 'N/A'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Total entries</span>
                          <span className="text-slate-200">{summary.total_content_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Total words</span>
                          <span className="text-slate-200">{summary.total_word_count?.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Vocabulary size</span>
                          <span className="text-slate-200">{summary.vocabulary_size?.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Avg words/entry</span>
                          <span className="text-slate-200">
                            {summary.total_content_count > 0 ? Math.round(summary.total_word_count / summary.total_content_count) : 0}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-800 p-3 rounded-b-lg border-t border-slate-700 flex justify-between items-center flex-shrink-0">
          <span className="text-xs text-slate-500">{summary?.total_content_count || 0} total entries</span>
          <div className="flex gap-2">
            <button
              onClick={fetchData}
              className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors px-3 py-1"
            >
              Refresh
            </button>
            <button
              onClick={onClose}
              className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-1 rounded-lg text-sm transition-colors font-semibold"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
