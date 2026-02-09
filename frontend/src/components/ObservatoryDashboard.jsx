import { useState, useEffect, useCallback } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { API_BASE } from '../utils/config';

const REFRESH_INTERVAL = 30000;

const COLORS = {
  cyan: '#06b6d4',
  purple: '#a855f7',
  green: '#22c55e',
  yellow: '#eab308',
  red: '#ef4444',
  blue: '#3b82f6',
  orange: '#f97316',
  pink: '#ec4899',
  slate: '#64748b',
};

const PIE_COLORS = [COLORS.cyan, COLORS.purple, COLORS.green, COLORS.orange, COLORS.pink];

const STATUS_COLORS = {
  healthy: COLORS.green,
  degraded: COLORS.yellow,
  offline: COLORS.red,
  unknown: COLORS.slate,
};

// --- Small reusable components ---

function StatCard({ label, value, sub, color = 'cyan', icon }) {
  const borderColor = {
    cyan: 'border-cyan-500/30',
    purple: 'border-purple-500/30',
    green: 'border-green-500/30',
    yellow: 'border-yellow-500/30',
    red: 'border-red-500/30',
    blue: 'border-blue-500/30',
  }[color] || 'border-cyan-500/30';

  const textColor = {
    cyan: 'text-cyan-400',
    purple: 'text-purple-400',
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
  }[color] || 'text-cyan-400';

  return (
    <div className={`bg-slate-900 rounded-xl p-4 border ${borderColor}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <div className={`text-2xl font-bold ${textColor}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

function ProgressBar({ value, max = 1, color = 'cyan', height = 'h-2' }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const bgColor = {
    cyan: 'bg-cyan-500',
    purple: 'bg-purple-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  }[color] || 'bg-cyan-500';

  return (
    <div className={`w-full bg-slate-700 rounded-full ${height}`}>
      <div className={`${height} rounded-full ${bgColor} transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function GaugeRing({ value, max = 1, size = 80, strokeWidth = 8, color = COLORS.cyan, label }) {
  const pct = max > 0 ? Math.min(value / max, 1) : 0;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - pct);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#334155" strokeWidth={strokeWidth} />
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={dashOffset} strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-sm font-bold text-white">{Math.round(pct * 100)}%</span>
      </div>
      {label && <span className="text-xs text-slate-400 mt-1">{label}</span>}
    </div>
  );
}

function SectionHeader({ title, icon }) {
  return (
    <div className="flex items-center gap-2 mb-4 mt-8 first:mt-0">
      {icon && <span className="text-xl">{icon}</span>}
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <div className="flex-1 h-px bg-slate-700 ml-2" />
    </div>
  );
}

function SubsystemCard({ name, icon, status, lastActivity, keyMetric }) {
  const dotColor = STATUS_COLORS[status] || STATUS_COLORS.unknown;
  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <span className="text-sm font-medium text-white">{name}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: dotColor }} />
          <span className="text-xs text-slate-400">{status}</span>
        </div>
      </div>
      <div className="text-xs text-slate-400 mb-1">{lastActivity}</div>
      <div className="text-sm text-cyan-400 font-medium">{keyMetric}</div>
    </div>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 shadow-xl">
      {label && <div className="text-xs text-slate-300 mb-1">{label}</div>}
      {payload.map((p, i) => (
        <div key={i} className="text-sm font-medium" style={{ color: p.color || COLORS.cyan }}>
          {p.name}: {typeof p.value === 'number' && p.value < 1 ? `$${p.value.toFixed(4)}` : p.value}
        </div>
      ))}
    </div>
  );
}

function PromptSlotCard({ slotId, data }) {
  const parts = slotId.split('.');
  const category = parts[0] || '';
  const action = parts[1] || '';
  const scoreColor = data.avg_score >= 0.7 ? COLORS.green : data.avg_score >= 0.4 ? COLORS.yellow : COLORS.red;

  const categoryIcons = {
    code_generator: '💻',
    tool_maker: '🔧',
    reflexion: '🪞',
  };

  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{categoryIcons[category] || '🧬'}</span>
        <div>
          <div className="text-sm font-medium text-white">{category}</div>
          <div className="text-xs text-slate-400">{action}</div>
        </div>
      </div>
      <div className="flex items-center gap-3 mb-2">
        <div className="relative flex items-center justify-center" style={{ width: 48, height: 48 }}>
          <svg width={48} height={48} className="-rotate-90">
            <circle cx={24} cy={24} r={18} fill="none" stroke="#334155" strokeWidth={5} />
            <circle cx={24} cy={24} r={18} fill="none" stroke={scoreColor} strokeWidth={5}
              strokeDasharray={113} strokeDashoffset={113 * (1 - data.avg_score)} strokeLinecap="round" />
          </svg>
          <span className="absolute text-xs font-bold text-white">{(data.avg_score * 100).toFixed(0)}</span>
        </div>
        <div className="flex-1 text-xs space-y-1">
          <div className="flex justify-between text-slate-400">
            <span>Uses</span><span className="text-white font-medium">{data.uses}</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Variants</span><span className="text-white font-medium">{data.variants}</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Retired</span><span className="text-white font-medium">{data.retired || 0}</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1">
        {data.is_original ? (
          <span className="px-2 py-0.5 rounded-full bg-slate-700 text-xs text-slate-300">original</span>
        ) : (
          <span className="px-2 py-0.5 rounded-full bg-purple-900/50 text-xs text-purple-300">mutated</span>
        )}
      </div>
    </div>
  );
}


// --- Main Component ---

export default function ObservatoryDashboard({ onBack }) {
  const [overview, setOverview] = useState(null);
  const [aiRouting, setAiRouting] = useState(null);
  const [evolution, setEvolution] = useState(null);
  const [subsystems, setSubsystems] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [ovRes, aiRes, evoRes, subRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/v1/observatory/overview`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/ai-routing`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/evolution`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/subsystems`).then(r => r.json()),
      ]);

      if (ovRes.status === 'fulfilled') setOverview(ovRes.value);
      if (aiRes.status === 'fulfilled') setAiRouting(aiRes.value);
      if (evoRes.status === 'fulfilled') setEvolution(evoRes.value);
      if (subRes.status === 'fulfilled') setSubsystems(subRes.value);

      setLastRefresh(new Date());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchAll]);

  // --- Derived chart data ---
  const modelPieData = aiRouting?.models
    ? Object.entries(aiRouting.models).map(([name, d]) => ({ name, value: d.requests })).filter(d => d.value > 0)
    : [];

  const tierBarData = aiRouting?.tier_distribution
    ? Object.entries(aiRouting.tier_distribution).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value }))
    : [];

  const costBarData = aiRouting?.models
    ? Object.entries(aiRouting.models).map(([name, d]) => ({ name, cost: d.cost })).filter(d => d.cost > 0)
    : [];

  const stateLabel = overview?.state === 'wake' ? 'Awake' : overview?.state === 'sleep' ? 'Sleeping' : 'Unknown';
  const stateEmoji = overview?.state === 'wake' ? '🌅' : overview?.state === 'sleep' ? '😴' : '❓';

  return (
    <div className="h-screen overflow-y-auto bg-slate-950 text-white">
      {/* Sticky Header */}
      <header className="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={onBack}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors text-sm text-slate-300 flex items-center gap-1">
              <span>←</span> Dashboard
            </button>
            <div className="flex items-center gap-2">
              <span className="text-2xl">📊</span>
              <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                Darwin Observatory
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {overview && (
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                overview.state === 'wake' ? 'bg-orange-900/40 text-orange-300' : 'bg-blue-900/40 text-blue-300'
              }`}>
                <span>{stateEmoji}</span>
                {stateLabel}
                <span className="text-xs opacity-70">{Math.round(overview.uptime_minutes || 0)}min</span>
              </div>
            )}
            <div className="text-xs text-slate-500">
              {lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString()}` : 'Loading...'}
              <span className="ml-2 inline-block w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" title="Auto-refresh 30s" />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 pb-12">
        {loading && !overview && (
          <div className="flex items-center justify-center py-20">
            <div className="text-lg text-slate-400 animate-pulse">Loading Observatory data...</div>
          </div>
        )}

        {error && !overview && (
          <div className="flex items-center justify-center py-20">
            <div className="text-red-400">Failed to load: {error}</div>
          </div>
        )}

        {/* SECTION 1: System Vitals */}
        {overview && (
          <>
            <SectionHeader title="System Vitals" icon="❤️" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="State" value={stateLabel} icon={stateEmoji} color={overview.state === 'wake' ? 'yellow' : 'blue'}
                sub={<ProgressBar value={overview.cycle_progress} color={overview.state === 'wake' ? 'yellow' : 'blue'} />}
              />
              <StatCard label="Wake Cycles" value={overview.wake_cycles} icon="🔄" color="purple"
                sub={`${overview.total_activities} activities`}
              />
              <StatCard label="Health" value={`${overview.subsystem_count.healthy}/${overview.subsystem_count.total}`} icon="✅" color="green"
                sub={`${overview.errors_last_hour} errors/hr`}
              />
              <StatCard label="Cost Today" value={`$${overview.cost_today.toFixed(3)}`} icon="💰" color="cyan"
                sub={`${overview.unread_findings} unread findings`}
              />
            </div>
          </>
        )}

        {/* SECTION 2: AI Nervous System */}
        {aiRouting && (
          <>
            <SectionHeader title="AI Nervous System" icon="🧠" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Model Distribution Pie */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Model Distribution</h3>
                {modelPieData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={modelPieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                        innerRadius={50} outerRadius={80} paddingAngle={2} strokeWidth={0}>
                        {modelPieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                      </Pie>
                      <Tooltip content={<ChartTooltip />} />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }}
                        formatter={(v) => <span className="text-slate-300">{v}</span>} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-slate-500 text-sm">No model data yet</div>
                )}
              </div>

              {/* Tier Routing Bar */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Tier Routing</h3>
                {tierBarData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={tierBarData} layout="vertical">
                      <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <YAxis dataKey="name" type="category" width={70} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <Tooltip content={<ChartTooltip />} />
                      <Bar dataKey="value" fill={COLORS.cyan} radius={[0, 4, 4, 0]} name="Requests" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-slate-500 text-sm">No routing data yet</div>
                )}
              </div>

              {/* Cost Breakdown */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Cost Breakdown</h3>
                {costBarData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={costBarData} layout="vertical">
                      <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={v => `$${v.toFixed(3)}`} />
                      <YAxis dataKey="name" type="category" width={70} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <Tooltip content={<ChartTooltip />} />
                      <Bar dataKey="cost" fill={COLORS.purple} radius={[0, 4, 4, 0]} name="Cost ($)" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-slate-500 text-sm">No cost data (all free tier!)</div>
                )}
              </div>

              {/* Free Tier Ratio */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50 flex flex-col items-center justify-center">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Free Tier Usage</h3>
                <div className="relative flex items-center justify-center">
                  <GaugeRing value={aiRouting.free_ratio} size={120} strokeWidth={12} color={COLORS.green} />
                </div>
                <div className="text-center mt-3">
                  <div className="text-2xl font-bold text-green-400">{(aiRouting.free_ratio * 100).toFixed(1)}%</div>
                  <div className="text-xs text-slate-500">{aiRouting.total_requests} total requests</div>
                  <div className="text-xs text-slate-500">Total cost: ${aiRouting.total_cost.toFixed(4)}</div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* SECTION 3: Evolution & Self-Improvement */}
        {evolution && (
          <>
            <SectionHeader title="Evolution & Self-Improvement" icon="🧬" />

            {/* Prompt Slot Cards */}
            {Object.keys(evolution.prompt_slots || {}).length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                {Object.entries(evolution.prompt_slots).map(([slotId, data]) => (
                  <PromptSlotCard key={slotId} slotId={slotId} data={data} />
                ))}
              </div>
            )}

            {/* Code Generation + Tools stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Slots" value={evolution.total_slots} color="purple" icon="🎰" />
              <StatCard label="Active Mutations" value={evolution.active_mutations} color="purple" icon="🧪" />
              <StatCard label="Tools Created" value={evolution.tools_created} color="cyan" icon="🔧"
                sub={`${(evolution.tool_success_rate * 100).toFixed(0)}% success`}
              />
              <StatCard label="Code Attempts" value={evolution.code_generation?.total_attempts || 0} color="green" icon="💻"
                sub={evolution.code_generation?.total_attempts > 0
                  ? `${((evolution.code_generation.first_try_pass / evolution.code_generation.total_attempts) * 100).toFixed(0)}% first-try`
                  : 'No data yet'}
              />
            </div>
          </>
        )}

        {/* SECTION 4: Consciousness & Mood */}
        {overview && (
          <>
            <SectionHeader title="Consciousness & Mood" icon="🌙" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Cycle Info */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Current Cycle</h3>
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-3xl">{stateEmoji}</span>
                  <div>
                    <div className="text-lg font-bold text-white">{stateLabel}</div>
                    <div className="text-xs text-slate-400">{Math.round(overview.uptime_minutes)}min elapsed</div>
                  </div>
                </div>
                <ProgressBar value={overview.cycle_progress} color={overview.state === 'wake' ? 'yellow' : 'blue'} height="h-3" />
                <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                  <div className="text-slate-400">Wake cycles: <span className="text-white font-medium">{overview.wake_cycles}</span></div>
                  <div className="text-slate-400">Sleep cycles: <span className="text-white font-medium">{overview.sleep_cycles}</span></div>
                </div>
              </div>

              {/* Mood Display */}
              <MoodDisplay subsystems={subsystems} />

              {/* Activity Summary */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Activity Summary</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Total Activities</span>
                    <span className="text-lg font-bold text-cyan-400">{overview.total_activities}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Discoveries</span>
                    <span className="text-lg font-bold text-purple-400">{overview.total_discoveries}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Errors (1h)</span>
                    <span className={`text-lg font-bold ${overview.errors_last_hour > 5 ? 'text-red-400' : 'text-green-400'}`}>
                      {overview.errors_last_hour}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Unread Findings</span>
                    <span className="text-lg font-bold text-yellow-400">{overview.unread_findings}</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* SECTION 5: Findings & Knowledge */}
        {subsystems && (
          <>
            <SectionHeader title="Findings & Knowledge" icon="📚" />
            <FindingsBreakdown subsystems={subsystems} />
          </>
        )}

        {/* SECTION 6: Subsystem Health Grid */}
        {subsystems?.subsystems && (
          <>
            <SectionHeader title="Subsystem Health" icon="🟢" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {subsystems.subsystems.map((sub, i) => (
                <SubsystemCard key={i} name={sub.name} icon={sub.icon} status={sub.status}
                  lastActivity={sub.last_activity} keyMetric={sub.key_metric} />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}


// --- Sub-components that need subsystem data ---

function MoodDisplay({ subsystems }) {
  const moodSub = subsystems?.subsystems?.find(s => s.name === 'Mood System');
  const details = moodSub?.details || {};
  const currentMood = details.mood || 'unknown';
  const intensity = details.intensity || 0;

  const moodColors = {
    curious: COLORS.cyan,
    excited: COLORS.yellow,
    focused: COLORS.blue,
    content: COLORS.green,
    anxious: COLORS.orange,
    frustrated: COLORS.red,
    calm: COLORS.purple,
  };

  const moodColor = moodColors[currentMood] || COLORS.slate;

  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
      <h3 className="text-sm font-medium text-slate-300 mb-3">Current Mood</h3>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-3xl">{moodSub?.icon || '🎭'}</span>
        <div>
          <div className="text-lg font-bold capitalize" style={{ color: moodColor }}>{currentMood}</div>
          <div className="text-xs text-slate-400">Intensity: {typeof intensity === 'number' ? intensity.toFixed(1) : intensity}</div>
        </div>
      </div>
      {details.time_in_mood_minutes !== undefined && (
        <div className="text-xs text-slate-400 mb-2">
          In this mood for {Math.round(details.time_in_mood_minutes)}min
        </div>
      )}
      {/* Intensity bar */}
      <div className="mt-2">
        <div className="text-xs text-slate-500 mb-1">Intensity</div>
        <div className="w-full bg-slate-700 rounded-full h-2">
          <div className="h-2 rounded-full transition-all duration-500" style={{
            width: `${(typeof intensity === 'number' ? intensity : 0.5) * 100}%`,
            backgroundColor: moodColor
          }} />
        </div>
      </div>
    </div>
  );
}

function FindingsBreakdown({ subsystems }) {
  const findingsSub = subsystems?.subsystems?.find(s => s.name === 'Findings Inbox');
  const byPriority = findingsSub?.details?.by_priority || {};
  const byType = findingsSub?.details?.by_type || {};

  const priorityColors = { urgent: COLORS.red, high: COLORS.orange, medium: COLORS.yellow, low: COLORS.slate };
  const typeColors = { discovery: COLORS.cyan, insight: COLORS.purple, anomaly: COLORS.red, suggestion: COLORS.green, curiosity: COLORS.yellow };

  const hasPriority = Object.values(byPriority).some(v => v > 0);
  const hasType = Object.values(byType).some(v => v > 0);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-3">Findings by Priority</h3>
        {hasPriority ? (
          <div className="space-y-2">
            {Object.entries(byPriority).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-xs text-slate-400 w-16 capitalize">{key}</span>
                <div className="flex-1 bg-slate-700 rounded-full h-3">
                  <div className="h-3 rounded-full transition-all" style={{
                    width: `${Math.min((val / Math.max(...Object.values(byPriority), 1)) * 100, 100)}%`,
                    backgroundColor: priorityColors[key] || COLORS.slate
                  }} />
                </div>
                <span className="text-xs text-white font-medium w-8 text-right">{val}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-slate-500">No findings data</div>
        )}
      </div>
      <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-3">Findings by Type</h3>
        {hasType ? (
          <div className="space-y-2">
            {Object.entries(byType).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-xs text-slate-400 w-16 capitalize">{key}</span>
                <div className="flex-1 bg-slate-700 rounded-full h-3">
                  <div className="h-3 rounded-full transition-all" style={{
                    width: `${Math.min((val / Math.max(...Object.values(byType), 1)) * 100, 100)}%`,
                    backgroundColor: typeColors[key] || COLORS.slate
                  }} />
                </div>
                <span className="text-xs text-white font-medium w-8 text-right">{val}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-slate-500">No findings data</div>
        )}
      </div>
    </div>
  );
}
