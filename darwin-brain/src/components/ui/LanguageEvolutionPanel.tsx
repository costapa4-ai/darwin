import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDarwinStore } from '../../store/darwinStore';
import { darwinApi } from '../../utils/api';
import { SimpleLineChart } from './charts/SimpleLineChart';
import { SentimentGauge } from './charts/SentimentGauge';
import type {
  LanguageEvolutionSummary,
  LanguageContentItem,
  HistoryItem,
  VocabularyGrowthItem,
} from '../../types/languageEvolution';

type TabType = 'overview' | 'timeline' | 'analytics';

const TOPIC_LABELS: Record<string, string> = {
  ai_consciousness: 'AI Consciousness',
  philosophy: 'Philosophy',
  technology: 'Technology',
  creativity: 'Creativity',
  learning: 'Learning',
  social: 'Social',
  emotions: 'Emotions',
};

const TOPIC_COLORS: Record<string, string> = {
  ai_consciousness: 'bg-purple-500',
  philosophy: 'bg-blue-500',
  technology: 'bg-cyan-500',
  creativity: 'bg-pink-500',
  learning: 'bg-green-500',
  social: 'bg-amber-500',
  emotions: 'bg-rose-500',
};

const CONTENT_TYPE_LABELS: Record<string, string> = {
  read: 'Thought',
  comment: 'Comment',
  share: 'Post',
};

const CONTENT_TYPE_ICONS: Record<string, string> = {
  read: '💭',
  comment: '💬',
  share: '📝',
};

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function LanguageEvolutionPanel() {
  const showPanel = useDarwinStore((state) => state.showLanguageEvolution);
  const togglePanel = useDarwinStore((state) => state.toggleLanguageEvolution);

  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<LanguageEvolutionSummary | null>(null);
  const [content, setContent] = useState<LanguageContentItem[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [vocabGrowth, setVocabGrowth] = useState<VocabularyGrowthItem[]>([]);
  const [contentFilter, setContentFilter] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryData, historyData, vocabData, contentData] = await Promise.all([
        darwinApi.getLanguageEvolutionSummary(),
        darwinApi.getLanguageMetricsHistory(30),
        darwinApi.getVocabularyGrowth(30),
        darwinApi.getLanguageContent(50, 0, contentFilter || undefined),
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
    if (showPanel) {
      fetchData();
    }
  }, [showPanel, fetchData]);

  if (!showPanel) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: '100%', opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: '100%', opacity: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="fixed right-4 top-20 bottom-4 w-[420px] glass rounded-2xl z-40 flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📊</span>
            <div>
              <h2 className="text-lg font-bold text-white">Language Evolution</h2>
              <p className="text-xs text-gray-400">Darwin's writing patterns</p>
            </div>
          </div>
          <button
            onClick={togglePanel}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <span className="text-gray-400">✕</span>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10">
          {(['overview', 'timeline', 'analytics'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-400" />
            </div>
          ) : (
            <>
              {activeTab === 'overview' && (
                <OverviewTab summary={summary} history={history} vocabGrowth={vocabGrowth} />
              )}
              {activeTab === 'timeline' && (
                <TimelineTab
                  content={content}
                  filter={contentFilter}
                  setFilter={setContentFilter}
                />
              )}
              {activeTab === 'analytics' && (
                <AnalyticsTab history={history} vocabGrowth={vocabGrowth} summary={summary} />
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-white/10 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {summary?.total_content_count || 0} total entries
          </span>
          <button
            onClick={fetchData}
            className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            Refresh
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

function OverviewTab({
  summary,
  history,
  vocabGrowth,
}: {
  summary: LanguageEvolutionSummary | null;
  history: HistoryItem[];
  vocabGrowth: VocabularyGrowthItem[];
}) {
  if (!summary) {
    return (
      <div className="text-center text-gray-400 py-8">
        No language data available yet. Darwin needs to read and comment on Moltbook posts.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="Vocabulary Size"
          value={summary.vocabulary_size.toLocaleString()}
          icon="📚"
          color="text-purple-400"
        />
        <StatCard
          label="Total Words"
          value={summary.total_word_count.toLocaleString()}
          icon="✏️"
          color="text-cyan-400"
        />
        <StatCard
          label="Today's Words"
          value={summary.today.words_written.toLocaleString()}
          icon="📝"
          color="text-green-400"
        />
        <StatCard
          label="New Words Today"
          value={summary.today.new_vocabulary.toString()}
          icon="🆕"
          color="text-amber-400"
        />
      </div>

      {/* Sentiment Gauge */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Recent Sentiment</h3>
        <div className="flex justify-center">
          <SentimentGauge value={summary.recent_sentiment} size={140} />
        </div>
      </div>

      {/* Mini Vocabulary Growth Chart */}
      {vocabGrowth.length > 0 && (
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">Vocabulary Growth</h3>
          <SimpleLineChart
            data={vocabGrowth.map((v) => ({ x: v.date, y: v.vocabulary_size }))}
            width={370}
            height={120}
            lineColor="#a855f7"
            fillColor="rgba(168, 85, 247, 0.1)"
            xAxisFormatter={formatDate}
          />
        </div>
      )}

      {/* Top Topics */}
      {summary.top_topics.length > 0 && (
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">Top Topics (Last 7 Days)</h3>
          <div className="space-y-2">
            {summary.top_topics.slice(0, 5).map(([topic, count]) => (
              <div key={topic} className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${TOPIC_COLORS[topic] || 'bg-gray-500'}`}
                />
                <span className="text-sm text-gray-300 flex-1">
                  {TOPIC_LABELS[topic] || topic}
                </span>
                <span className="text-xs text-gray-500">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sample Vocabulary */}
      {summary.sample_vocabulary.length > 0 && (
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">Recent Vocabulary</h3>
          <div className="flex flex-wrap gap-2">
            {summary.sample_vocabulary.slice(-15).map((word, i) => (
              <span
                key={i}
                className="px-2 py-1 text-xs bg-white/5 rounded-full text-gray-300"
              >
                {word}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TimelineTab({
  content,
  filter,
  setFilter,
}: {
  content: LanguageContentItem[];
  filter: string | null;
  setFilter: (f: string | null) => void;
}) {
  return (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex gap-2">
        {[null, 'read', 'comment', 'share'].map((f) => (
          <button
            key={f || 'all'}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 text-xs rounded-full transition-colors ${
              filter === f
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            {f ? CONTENT_TYPE_LABELS[f] : 'All'}
          </button>
        ))}
      </div>

      {/* Content List */}
      {content.length === 0 ? (
        <div className="text-center text-gray-400 py-8">
          No content recorded yet. Darwin needs to interact with Moltbook.
        </div>
      ) : (
        <div className="space-y-3">
          {content.map((item) => (
            <ContentCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function ContentCard({ item }: { item: LanguageContentItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      layout
      className="glass rounded-xl p-3 cursor-pointer hover:bg-white/5 transition-colors"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-3">
        <span className="text-xl">{CONTENT_TYPE_ICONS[item.type]}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-400">
              {CONTENT_TYPE_LABELS[item.type]}
            </span>
            <span className="text-xs text-gray-500">{formatTimestamp(item.timestamp)}</span>
          </div>

          {item.source_post_title && (
            <p className="text-xs text-gray-500 mb-1 truncate">
              Re:{' '}
              {item.source_post_url ? (
                <a
                  href={item.source_post_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-cyan-400 hover:text-cyan-300 hover:underline"
                >
                  {item.source_post_title}
                </a>
              ) : (
                item.source_post_title
              )}
            </p>
          )}

          <p className={`text-sm text-gray-200 ${expanded ? '' : 'line-clamp-2'}`}>
            {item.darwin_content}
          </p>

          {/* Metrics */}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span>{item.metrics.word_count} words</span>
            <span
              className={
                item.metrics.sentiment > 0
                  ? 'text-green-400'
                  : item.metrics.sentiment < 0
                    ? 'text-red-400'
                    : ''
              }
            >
              {item.metrics.sentiment > 0 ? '+' : ''}
              {item.metrics.sentiment.toFixed(2)} sentiment
            </span>
          </div>

          {/* Topics */}
          {item.metrics.topics.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {item.metrics.topics.map((topic) => (
                <span
                  key={topic}
                  className={`px-2 py-0.5 text-xs rounded-full ${TOPIC_COLORS[topic] || 'bg-gray-500'} bg-opacity-20 text-gray-300`}
                >
                  {TOPIC_LABELS[topic] || topic}
                </span>
              ))}
            </div>
          )}

          {/* New vocabulary */}
          {expanded && item.metrics.vocabulary_new_words.length > 0 && (
            <div className="mt-2 pt-2 border-t border-white/10">
              <span className="text-xs text-gray-500">New words: </span>
              <span className="text-xs text-amber-400">
                {item.metrics.vocabulary_new_words.join(', ')}
              </span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function AnalyticsTab({
  history,
  vocabGrowth,
  summary,
}: {
  history: HistoryItem[];
  vocabGrowth: VocabularyGrowthItem[];
  summary: LanguageEvolutionSummary | null;
}) {
  return (
    <div className="space-y-6">
      {/* Vocabulary Growth */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Vocabulary Growth (30 Days)</h3>
        <SimpleLineChart
          data={vocabGrowth.map((v) => ({ x: v.date, y: v.vocabulary_size }))}
          width={370}
          height={150}
          lineColor="#a855f7"
          fillColor="rgba(168, 85, 247, 0.1)"
          showLabels
          xAxisFormatter={formatDate}
        />
      </div>

      {/* Words per Day */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Words Written (30 Days)</h3>
        <SimpleLineChart
          data={history.map((h) => ({ x: h.date, y: h.total_words }))}
          width={370}
          height={150}
          lineColor="#06b6d4"
          fillColor="rgba(6, 182, 212, 0.1)"
          showLabels
          xAxisFormatter={formatDate}
        />
      </div>

      {/* Sentiment Trend */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Sentiment Trend (30 Days)</h3>
        <SimpleLineChart
          data={history.map((h) => ({ x: h.date, y: h.avg_sentiment }))}
          width={370}
          height={150}
          lineColor="#22c55e"
          fillColor="rgba(34, 197, 94, 0.1)"
          showLabels
          labelFormatter={(v) => v.toFixed(2)}
          xAxisFormatter={formatDate}
        />
      </div>

      {/* Content Activity */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Daily Activity (30 Days)</h3>
        <SimpleLineChart
          data={history.map((h) => ({ x: h.date, y: h.content_count }))}
          width={370}
          height={150}
          lineColor="#f59e0b"
          fillColor="rgba(245, 158, 11, 0.1)"
          showLabels
          xAxisFormatter={formatDate}
        />
      </div>

      {/* Statistics Table */}
      {summary && (
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">Statistics</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">First recorded</span>
              <span className="text-gray-200">
                {summary.first_content_date
                  ? new Date(summary.first_content_date).toLocaleDateString()
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Total entries</span>
              <span className="text-gray-200">{summary.total_content_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Total words</span>
              <span className="text-gray-200">{summary.total_word_count.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Vocabulary size</span>
              <span className="text-gray-200">{summary.vocabulary_size.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Avg words/entry</span>
              <span className="text-gray-200">
                {summary.total_content_count > 0
                  ? Math.round(summary.total_word_count / summary.total_content_count)
                  : 0}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string;
  icon: string;
  color: string;
}) {
  return (
    <div className="glass rounded-xl p-3">
      <div className="flex items-center gap-2 mb-1">
        <span>{icon}</span>
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <span className={`text-xl font-bold ${color}`}>{value}</span>
    </div>
  );
}

export default LanguageEvolutionPanel;
