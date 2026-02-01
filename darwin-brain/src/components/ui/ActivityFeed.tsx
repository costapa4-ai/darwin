import { motion, AnimatePresence } from 'framer-motion';
import { useDarwinStore } from '../../store/darwinStore';

const activityIcons = {
  code_optimization: '⚡',
  tool_creation: '🛠️',
  idea_implementation: '💡',
  curiosity_share: '🔍',
  self_improvement: '🔬',
};

const activityColors = {
  code_optimization: 'border-green-500/30 bg-green-500/5',
  tool_creation: 'border-orange-500/30 bg-orange-500/5',
  idea_implementation: 'border-blue-500/30 bg-blue-500/5',
  curiosity_share: 'border-purple-500/30 bg-purple-500/5',
  self_improvement: 'border-red-500/30 bg-red-500/5',
};

export function ActivityFeed() {
  const activities = useDarwinStore((state) => state.activities);
  const discoveries = useDarwinStore((state) => state.discoveries);
  const dreams = useDarwinStore((state) => state.dreams);
  const status = useDarwinStore((state) => state.status);

  // Combine and sort by timestamp
  const allItems = [
    ...activities.map((a) => ({ ...a, itemType: 'activity' as const })),
    ...discoveries.map((d) => ({ ...d, itemType: 'discovery' as const })),
    ...dreams.map((d) => ({ ...d, itemType: 'dream' as const })),
  ].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="fixed bottom-4 left-4 w-80 z-40"
    >
      <div className="glass rounded-2xl overflow-hidden max-h-[40vh]">
        {/* Header */}
        <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">📡</span>
            <h3 className="font-semibold text-white text-sm">Activity Feed</h3>
          </div>
          <div className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${
              status.state === 'wake' ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'
            }`} />
            <span className="text-xs text-gray-400 capitalize">{status.state}</span>
          </div>
        </div>

        {/* Feed Items */}
        <div className="overflow-y-auto max-h-[calc(40vh-48px)] p-2 space-y-2">
          <AnimatePresence mode="popLayout">
            {allItems.slice(0, 15).map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: 20, opacity: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                {item.itemType === 'activity' && (
                  <ActivityItem activity={item} />
                )}
                {item.itemType === 'discovery' && (
                  <DiscoveryItem discovery={item} />
                )}
                {item.itemType === 'dream' && (
                  <DreamItem dream={item} />
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {allItems.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <span className="text-2xl mb-2 block">🔮</span>
              <p className="text-sm">Waiting for activity...</p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function ActivityItem({ activity }: { activity: { type: string; title: string; timestamp: Date } }) {
  const icon = activityIcons[activity.type as keyof typeof activityIcons] || '📌';
  const colorClass = activityColors[activity.type as keyof typeof activityColors] || 'border-gray-500/30 bg-gray-500/5';

  return (
    <div className={`p-2 rounded-lg border ${colorClass}`}>
      <div className="flex items-start gap-2">
        <span className="text-sm">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-white truncate">{activity.title}</p>
          <p className="text-xs text-gray-500">
            {new Date(activity.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
      </div>
    </div>
  );
}

function DiscoveryItem({ discovery }: { discovery: { title: string; severity: string; timestamp: Date } }) {
  const severityColors = {
    normal: 'border-green-500/30 bg-green-500/5',
    important: 'border-yellow-500/30 bg-yellow-500/5',
    critical: 'border-red-500/30 bg-red-500/5',
  };

  return (
    <div className={`p-2 rounded-lg border ${severityColors[discovery.severity as keyof typeof severityColors] || severityColors.normal}`}>
      <div className="flex items-start gap-2">
        <span className="text-sm">🔍</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-white truncate">{discovery.title}</p>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-1.5 py-0.5 rounded capitalize ${
              discovery.severity === 'critical' ? 'bg-red-500/20 text-red-300' :
              discovery.severity === 'important' ? 'bg-yellow-500/20 text-yellow-300' :
              'bg-green-500/20 text-green-300'
            }`}>
              {discovery.severity}
            </span>
            <p className="text-xs text-gray-500">
              {new Date(discovery.timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function DreamItem({ dream }: { dream: { narrative: string; themes: string[]; timestamp: Date } }) {
  return (
    <div className="p-2 rounded-lg border border-purple-500/30 bg-purple-500/5">
      <div className="flex items-start gap-2">
        <span className="text-sm">💭</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-white line-clamp-2">{dream.narrative}</p>
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            {dream.themes?.slice(0, 2).map((theme, i) => (
              <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300">
                {theme}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ActivityFeed;
