import { motion, AnimatePresence } from 'framer-motion';
import { useDarwinStore } from '../../store/darwinStore';

const priorityColors = {
  urgent: 'border-red-500/30 bg-red-500/10 text-red-300',
  high: 'border-orange-500/30 bg-orange-500/10 text-orange-300',
  medium: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300',
  low: 'border-green-500/30 bg-green-500/10 text-green-300',
};

const typeIcons = {
  security: '🔒',
  performance: '⚡',
  bug: '🐛',
  improvement: '💡',
  discovery: '🔍',
  warning: '⚠️',
};

export function FindingsPanel() {
  const showFindings = useDarwinStore((state) => state.showFindings);
  const toggleFindings = useDarwinStore((state) => state.toggleFindings);
  const findings = useDarwinStore((state) => state.findings);
  const unreadCount = useDarwinStore((state) => state.unreadCount);

  return (
    <AnimatePresence>
      {showFindings && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed right-4 top-20 bottom-4 w-96 z-40"
        >
          <div className="h-full glass rounded-2xl flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">📋</span>
                <div>
                  <h3 className="font-semibold text-white">Findings</h3>
                  <p className="text-xs text-gray-400">
                    {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
                  </p>
                </div>
              </div>
              <button
                onClick={toggleFindings}
                className="p-1 rounded-lg hover:bg-white/10 transition-colors"
              >
                <span className="text-gray-400">✕</span>
              </button>
            </div>

            {/* Findings List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {findings.length === 0 ? (
                <div className="text-center text-gray-500 mt-8">
                  <span className="text-4xl mb-2 block">🔍</span>
                  <p>No findings yet</p>
                  <p className="text-sm mt-1">Darwin will report discoveries here</p>
                </div>
              ) : (
                findings.map((finding) => (
                  <FindingCard key={finding.id} finding={finding} />
                ))
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

interface FindingCardProps {
  finding: {
    id: string;
    title: string;
    description: string;
    type: string;
    priority: string;
    read: boolean;
    timestamp: Date;
    actions?: string[];
  };
}

function FindingCard({ finding }: FindingCardProps) {
  const icon = typeIcons[finding.type as keyof typeof typeIcons] || '📌';
  const colorClass = priorityColors[finding.priority as keyof typeof priorityColors] || priorityColors.medium;

  return (
    <motion.div
      initial={{ y: 10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className={`p-3 rounded-xl border ${colorClass} ${!finding.read ? 'ring-1 ring-white/20' : ''}`}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium text-white truncate">
              {finding.title}
            </h4>
            {!finding.read && (
              <span className="w-2 h-2 rounded-full bg-cyan-500" />
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1 line-clamp-2">
            {finding.description}
          </p>

          {finding.actions && finding.actions.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {finding.actions.slice(0, 2).map((action, i) => (
                <span
                  key={i}
                  className="text-xs px-2 py-0.5 rounded bg-white/5 text-gray-300"
                >
                  {action}
                </span>
              ))}
            </div>
          )}

          <p className="text-xs text-gray-500 mt-2">
            {new Date(finding.timestamp).toLocaleString([], {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
      </div>
    </motion.div>
  );
}

export default FindingsPanel;
