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
  const [safetyEvents, setSafetyEvents] = useState(null);
  const [moodEnv, setMoodEnv] = useState(null);
  const [growthIdentity, setGrowthIdentity] = useState(null);
  const [watchdogData, setWatchdogData] = useState(null);
  const [curiosity, setCuriosity] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [ovRes, aiRes, evoRes, subRes, safetyRes, moodRes, growthRes, wdRes, cuRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/v1/observatory/overview`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/ai-routing`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/evolution`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/subsystems`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/safety-events`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/mood-environment`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/growth-identity`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/interest-watchdog`).then(r => r.json()),
        fetch(`${API_BASE}/api/v1/observatory/curiosity`).then(r => r.json()),
      ]);

      if (ovRes.status === 'fulfilled') setOverview(ovRes.value);
      if (aiRes.status === 'fulfilled') setAiRouting(aiRes.value);
      if (evoRes.status === 'fulfilled') setEvolution(evoRes.value);
      if (subRes.status === 'fulfilled') setSubsystems(subRes.value);
      if (safetyRes.status === 'fulfilled') setSafetyEvents(safetyRes.value);
      if (moodRes.status === 'fulfilled') setMoodEnv(moodRes.value);
      if (growthRes.status === 'fulfilled') setGrowthIdentity(growthRes.value);
      if (wdRes.status === 'fulfilled') setWatchdogData(wdRes.value);
      if (cuRes.status === 'fulfilled') setCuriosity(cuRes.value);

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
                <span className="text-xs opacity-70">
                  {Math.round(overview.uptime_minutes || 0)}m/{overview.state === 'wake' ? (overview.wake_duration || 120) : (overview.sleep_duration || 30)}m
                </span>
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
            {/* Stream / Memory / Safety stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <StatCard label="Stream Events" value={overview.stream_events ?? 0} icon="🌊" color="cyan"
                sub="total consciousness events" />
              <StatCard label="Memory Episodes" value={overview.memory_episodes ?? 0} icon="🧠" color="purple"
                sub={`${overview.semantic_knowledge ?? 0} semantic knowledge`} />
              <StatCard label="Safety Events" value={overview.safety_events_24h ?? 0} icon="🛡️" color="yellow"
                sub="last 24 hours" />
              <StatCard label="Subsystems" value={`${overview.subsystem_count?.healthy ?? 0}/${overview.subsystem_count?.total ?? 0}`} icon="✅" color="green"
                sub={`${overview.subsystem_count?.degraded ?? 0} degraded`} />
            </div>

            {/* Environmental Factors */}
            {moodEnv?.environment && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4">
                <StatCard label="Discovery Momentum"
                  value={`${Math.round((moodEnv.environment.discovery_momentum || 0) * 100)}%`}
                  icon="🚀" color="green"
                  sub={<ProgressBar value={moodEnv.environment.discovery_momentum || 0} color="green" />} />
                <StatCard label="Frustration Level"
                  value={`${Math.round((moodEnv.environment.frustration_level || 0) * 100)}%`}
                  icon="😤" color="red"
                  sub={<ProgressBar value={moodEnv.environment.frustration_level || 0} color="red" />} />
                <StatCard label="Engagement"
                  value={`${Math.round((moodEnv.environment.engagement_level || 0) * 100)}%`}
                  icon="⚡" color="cyan"
                  sub={<ProgressBar value={moodEnv.environment.engagement_level || 0} color="cyan" />} />
                <StatCard label="Discoveries Today" value={moodEnv.environment.discoveries_today ?? 0}
                  icon="💡" color="yellow" />
                <StatCard label="Errors Today" value={moodEnv.environment.errors_today ?? 0}
                  icon="❌" color="red" />
              </div>
            )}

            {/* Mood Statistics + Distribution */}
            {moodEnv?.statistics && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                  <h3 className="text-sm font-medium text-slate-300 mb-3">Mood Statistics</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-xs text-slate-400">Total Transitions</span>
                      <span className="text-lg font-bold text-cyan-400">
                        {moodEnv.statistics.total_transitions ?? 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-slate-400">Avg Duration</span>
                      <span className="text-lg font-bold text-purple-400">
                        {Math.round(moodEnv.statistics.average_mood_duration_minutes ?? 0)}min
                      </span>
                    </div>
                    {moodEnv.statistics.most_common_moods && (
                      <div>
                        <span className="text-xs text-slate-400">Most Common</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Object.entries(moodEnv.statistics.most_common_moods).slice(0, 3).map(([mood, count]) => (
                            <span key={mood} className="px-2 py-0.5 rounded-full bg-slate-800 text-xs text-slate-300 capitalize">
                              {mood} ({count})
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <MoodDistributionChart distribution={moodEnv.statistics.mood_distribution} />
              </div>
            )}
          </>
        )}

        {/* SECTION 5: Memory & Conversations */}
        {growthIdentity?.conversations && (
          <>
            <SectionHeader title="Memory & Conversations" icon="💬" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Messages" value={growthIdentity.conversations.total_messages ?? 0}
                icon="💬" color="cyan"
                sub={`${growthIdentity.conversations.daily_summaries ?? 0} daily summaries`} />
              <StatCard label="Paulo Messages" value={growthIdentity.conversations.user_messages ?? 0}
                icon="👤" color="blue" />
              <StatCard label="Darwin Messages" value={growthIdentity.conversations.darwin_messages ?? 0}
                icon="🤖" color="purple" />
              <StatCard label="Relationship Facts" value={growthIdentity.conversations.relationship_facts ?? 0}
                icon="🤝" color="green" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {/* Messages by Channel */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Messages by Channel</h3>
                {Object.keys(growthIdentity.conversations.messages_by_channel || {}).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(growthIdentity.conversations.messages_by_channel).map(([ch, count]) => {
                      const maxCount = Math.max(...Object.values(growthIdentity.conversations.messages_by_channel), 1);
                      return (
                        <div key={ch} className="flex items-center gap-2">
                          <span className="text-xs text-slate-400 w-20 capitalize">{ch}</span>
                          <div className="flex-1 bg-slate-700 rounded-full h-3">
                            <div className="h-3 rounded-full bg-cyan-500 transition-all"
                              style={{ width: `${(count / maxCount) * 100}%` }} />
                          </div>
                          <span className="text-xs text-white font-medium w-10 text-right">{count}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-sm text-slate-500">No channel data</div>
                )}
              </div>
              {/* Memory Overview */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Memory System</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Episodic Memory</span>
                    <span className="text-lg font-bold text-purple-400">{overview?.memory_episodes ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Semantic Knowledge</span>
                    <span className="text-lg font-bold text-cyan-400">{overview?.semantic_knowledge ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Stream Events</span>
                    <span className="text-lg font-bold text-yellow-400">{overview?.stream_events ?? 0}</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* SECTION 6: Growth & Identity */}
        {growthIdentity && (
          <>
            <SectionHeader title="Growth & Identity" icon="🌱" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Genome Version"
                value={`v${growthIdentity.genome?.version ?? '?'}`}
                icon="🧬" color="purple"
                sub={growthIdentity.genome?.can_evolve ? 'Ready to evolve' :
                  `${growthIdentity.genome?.cycles_since_last_mutation ?? 0}/${growthIdentity.genome?.mutation_cooldown_cycles ?? 10} cycles`} />
              <StatCard label="Total Mutations"
                value={growthIdentity.genome?.stats?.total_mutations ?? 0}
                icon="🔀" color="cyan"
                sub={`${growthIdentity.genome?.stats?.kept_mutations ?? 0} kept, ${growthIdentity.genome?.stats?.rolledback_mutations ?? 0} rolled back`} />
              <StatCard label="Vocabulary Size"
                value={growthIdentity.language?.vocabulary_size ?? 0}
                icon="📖" color="green"
                sub={`${growthIdentity.language?.total_word_count ?? 0} total words`} />
              <StatCard label="Sentiment"
                value={growthIdentity.language?.recent_sentiment !== undefined
                  ? (growthIdentity.language.recent_sentiment >= 0 ? '+' : '') + growthIdentity.language.recent_sentiment.toFixed(2)
                  : 'N/A'}
                icon="📊"
                color={(growthIdentity.language?.recent_sentiment ?? 0) >= 0 ? 'green' : 'red'}
                sub="7-day average" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <GenomeDomainChart perDomain={growthIdentity.genome?.stats?.per_domain} />
              {/* Darwin Identity */}
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Darwin Identity</h3>
                <div className="space-y-3">
                  {growthIdentity.darwin_identity?.core_values?.length > 0 && (
                    <div>
                      <span className="text-xs text-slate-400">Core Values</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {growthIdentity.darwin_identity.core_values.map((v, i) => (
                          <span key={i} className="px-2 py-0.5 rounded-full bg-purple-900/40 text-xs text-purple-300 capitalize">
                            {v}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Interests</span>
                    <span className="text-lg font-bold text-cyan-400">
                      {growthIdentity.darwin_identity?.interests_count ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Opinions Formed</span>
                    <span className="text-lg font-bold text-purple-400">
                      {growthIdentity.darwin_identity?.opinions_count ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Growth Milestones</span>
                    <span className="text-lg font-bold text-green-400">
                      {growthIdentity.darwin_identity?.milestones_count ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Facts about Paulo</span>
                    <span className="text-lg font-bold text-yellow-400">
                      {growthIdentity.paulo_model?.known_facts ?? 0}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            {/* Language top topics */}
            {growthIdentity.language?.top_topics?.length > 0 && (
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50 mt-4">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Top Topics (7 days)</h3>
                <div className="space-y-2">
                  {growthIdentity.language.top_topics.map(([topic, count], i) => {
                    const maxCount = Math.max(...growthIdentity.language.top_topics.map(t => t[1]), 1);
                    return (
                      <div key={topic} className="flex items-center gap-2">
                        <span className="text-xs text-slate-400 w-32 truncate capitalize">{topic}</span>
                        <div className="flex-1 bg-slate-700 rounded-full h-3">
                          <div className="h-3 rounded-full transition-all" style={{
                            width: `${(count / maxCount) * 100}%`,
                            backgroundColor: PIE_COLORS[i % PIE_COLORS.length]
                          }} />
                        </div>
                        <span className="text-xs text-white font-medium w-8 text-right">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}

        {/* SECTION 7: Goals & Interests */}
        {growthIdentity && (
          <>
            <SectionHeader title="Goals & Interests" icon="🎯" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Pending Goals" value={growthIdentity.intentions?.pending ?? 0}
                icon="📋" color="yellow" />
              <StatCard label="In Progress" value={growthIdentity.intentions?.in_progress ?? 0}
                icon="⏳" color="cyan" />
              <StatCard label="Completed" value={growthIdentity.intentions?.completed ?? 0}
                icon="✅" color="green" />
              <StatCard label="Expired" value={growthIdentity.intentions?.expired ?? 0}
                icon="⏰" color="red" />
            </div>
            {growthIdentity.interests?.active_interests &&
             Object.keys(growthIdentity.interests.active_interests).length > 0 && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-300">
                    Active Interests ({growthIdentity.interests.active_count ?? 0}/7)
                  </h3>
                  <span className="text-xs text-slate-500">
                    {growthIdentity.interests.dormant_count ?? 0} dormant · {Math.round(growthIdentity.interests.total_exploration_minutes ?? 0)}min total
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {Object.entries(growthIdentity.interests.active_interests).map(([key, interest]) => (
                    <InterestCard key={key} interest={interest} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* SECTION 7B: Interest Watchdog */}
        {watchdogData && watchdogData.status === 'active' && (
          <>
            <SectionHeader title="Interest Watchdog" icon="🔍" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Observations" value={watchdogData.stats?.total_observations ?? 0}
                icon="👁" color="purple" />
              <StatCard label="Registered" value={watchdogData.stats?.total_registered ?? 0}
                icon="✅" color="green" />
              <StatCard label="This Cycle" value={`${watchdogData.stats?.new_this_cycle ?? 0}/${watchdogData.stats?.max_per_cycle ?? 3}`}
                icon="🔄" color="cyan" />
              <StatCard label="Seen Topics" value={watchdogData.stats?.seen_topics_count ?? 0}
                icon="📝" color="yellow" />
            </div>
            {watchdogData.history?.length > 0 && (
              <div className="mt-4 bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Recent Observations</h3>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {watchdogData.history.map((obs, i) => (
                    <WatchdogObservation key={i} obs={obs} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* SECTION 7C: Curiosity Exploration */}
        {curiosity && curiosity.by_depth && (
          <>
            <SectionHeader title="Curiosity Exploration" icon="🔬" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Satisfied" value={curiosity.totals?.satisfied ?? 0}
                icon="✅" color="green" sub={`of ${(curiosity.totals?.satisfied ?? 0) + (curiosity.totals?.exploring ?? 0) + (curiosity.totals?.pending ?? 0) + (curiosity.totals?.expired ?? 0)} total`} />
              <StatCard label="Knowledge Stored" value={curiosity.totals?.total_knowledge_stored ?? 0}
                icon="💾" color="purple" />
              <StatCard label="Pending" value={curiosity.totals?.pending ?? 0}
                icon="⏳" color="yellow" sub={`${curiosity.totals?.exploring ?? 0} exploring`} />
              <StatCard label="Expired" value={curiosity.totals?.expired ?? 0}
                icon="💀" color="red" />
            </div>

            {/* Depth threshold table */}
            <div className="mt-4 bg-slate-900 rounded-xl p-4 border border-slate-700/50">
              <h3 className="text-sm font-medium text-slate-300 mb-3">Satisfaction by Depth Level</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-700">
                      <th className="text-left py-2 px-3">Depth</th>
                      <th className="text-center py-2 px-3">Threshold</th>
                      <th className="text-center py-2 px-3">Reached</th>
                      <th className="text-center py-2 px-3">Rate</th>
                      <th className="text-center py-2 px-3">Avg %</th>
                      <th className="text-center py-2 px-3">Max %</th>
                      <th className="text-center py-2 px-3">Knowledge</th>
                      <th className="text-center py-2 px-3">Pending</th>
                      <th className="text-center py-2 px-3">Exploring</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(curiosity.by_depth).map(([depth, d]) => {
                      const rateColor = d.threshold_rate >= 20 ? 'text-green-400' : d.threshold_rate >= 5 ? 'text-yellow-400' : 'text-red-400';
                      return (
                        <tr key={depth} className="border-b border-slate-800 hover:bg-slate-800/50">
                          <td className="py-2 px-3 text-slate-200 font-medium">
                            {d.label} <span className="text-slate-500">(d{depth})</span>
                          </td>
                          <td className="text-center py-2 px-3 text-cyan-400">{d.threshold}%</td>
                          <td className="text-center py-2 px-3 text-slate-200">{d.reached_threshold}/{d.total_explored}</td>
                          <td className={`text-center py-2 px-3 font-medium ${rateColor}`}>{d.threshold_rate?.toFixed(0)}%</td>
                          <td className="text-center py-2 px-3 text-slate-300">{d.avg_satisfaction?.toFixed(0)}%</td>
                          <td className="text-center py-2 px-3 text-green-400">{d.max_satisfaction}%</td>
                          <td className="text-center py-2 px-3 text-purple-400">{d.knowledge_stored}</td>
                          <td className="text-center py-2 px-3 text-yellow-400">{d.pending}</td>
                          <td className="text-center py-2 px-3 text-cyan-400">{d.exploring}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recent explorations */}
            {curiosity.recent?.length > 0 && (
              <div className="mt-4 bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Recent Explorations</h3>
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {curiosity.recent.map((item, i) => (
                    <div key={i} className="flex items-center gap-2 py-1 px-2 rounded hover:bg-slate-800/50 text-xs">
                      <span>{item.met_threshold ? '✅' : '❌'}</span>
                      <span>{item.knowledge_stored ? '💾' : '  '}</span>
                      <span className="text-slate-500 w-8">d{item.depth}</span>
                      <span className={`w-10 text-right font-mono ${item.satisfaction >= (curiosity.thresholds?.[String(item.depth)] ?? 50) ? 'text-green-400' : item.satisfaction >= 20 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {item.satisfaction}%
                      </span>
                      <span className={`w-16 text-center rounded px-1 ${
                        item.status === 'satisfied' ? 'bg-green-900/30 text-green-400' :
                        item.status === 'exploring' ? 'bg-cyan-900/30 text-cyan-400' :
                        item.status === 'expired' ? 'bg-red-900/30 text-red-400' :
                        'bg-slate-800 text-slate-400'
                      }`}>{item.status}</span>
                      <span className="text-slate-300 truncate flex-1">{item.question}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* SECTION 8: Safety & Audit Trail */}
        {safetyEvents && Object.keys(safetyEvents.summary || {}).length > 0 && (
          <>
            <SectionHeader title="Safety & Audit Trail" icon="🛡️" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Safety Events (24h)</h3>
                <div className="space-y-2">
                  {Object.entries(safetyEvents.summary).map(([type, count]) => {
                    const maxCount = Math.max(...Object.values(safetyEvents.summary), 1);
                    const typeColors = {
                      model_fallback: COLORS.yellow,
                      routing_decision: COLORS.cyan,
                      truncation_retry: COLORS.orange,
                      code_validation_fail: COLORS.red,
                      code_validation_corrected: COLORS.green,
                      tool_rejected: COLORS.red,
                      prompt_rollback: COLORS.orange,
                      prompt_promoted: COLORS.green,
                      protected_file_redirect: COLORS.purple,
                      early_stop: COLORS.slate,
                    };
                    return (
                      <div key={type} className="flex items-center gap-2">
                        <span className="text-xs text-slate-400 w-40 truncate" title={type}>
                          {type.replace(/_/g, ' ')}
                        </span>
                        <div className="flex-1 bg-slate-700 rounded-full h-3">
                          <div className="h-3 rounded-full transition-all" style={{
                            width: `${Math.min((count / maxCount) * 100, 100)}%`,
                            backgroundColor: typeColors[type] || COLORS.slate
                          }} />
                        </div>
                        <span className="text-xs text-white font-medium w-8 text-right">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50 flex flex-col items-center justify-center">
                <h3 className="text-sm font-medium text-slate-300 mb-4">Total Safety Events</h3>
                <div className="text-5xl font-bold text-yellow-400">{safetyEvents.total_all_time ?? 0}</div>
                <div className="text-xs text-slate-500 mt-2">all time</div>
                <div className="text-lg font-medium text-slate-300 mt-3">
                  {Object.values(safetyEvents.summary || {}).reduce((a, b) => a + b, 0)} <span className="text-xs text-slate-500">last 24h</span>
                </div>
              </div>
            </div>
          </>
        )}

        {/* SECTION 9: Findings & Knowledge */}
        {subsystems && (
          <>
            <SectionHeader title="Findings & Knowledge" icon="📚" />
            <FindingsBreakdown subsystems={subsystems} />
          </>
        )}

        {/* SECTION 10: Subsystem Health Grid */}
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

function MoodDistributionChart({ distribution }) {
  if (!distribution || Object.keys(distribution).length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-3">Mood Distribution</h3>
        <div className="h-[200px] flex items-center justify-center text-slate-500 text-sm">No mood data yet</div>
      </div>
    );
  }
  const data = Object.entries(distribution)
    .map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value }))
    .sort((a, b) => b.value - a.value);

  const moodBarColors = {
    Curious: COLORS.cyan, Excited: COLORS.yellow, Focused: COLORS.blue,
    Satisfied: COLORS.green, Frustrated: COLORS.red, Tired: COLORS.slate,
    Playful: COLORS.pink, Contemplative: COLORS.purple, Determined: COLORS.orange,
    Surprised: COLORS.yellow, Confused: COLORS.orange, Proud: COLORS.green,
    Content: COLORS.green, Calm: COLORS.purple, Anxious: COLORS.orange,
  };

  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
      <h3 className="text-sm font-medium text-slate-300 mb-3">Mood Distribution</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis dataKey="name" type="category" width={90} tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="value" name="Count" radius={[0, 4, 4, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={moodBarColors[entry.name] || COLORS.slate} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function GenomeDomainChart({ perDomain }) {
  if (!perDomain || Object.keys(perDomain).length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300 mb-3">Mutations per Domain</h3>
        <div className="h-[200px] flex items-center justify-center text-slate-500 text-sm">No mutation data yet</div>
      </div>
    );
  }
  const data = Object.entries(perDomain).map(([domain, stats]) => ({
    name: domain.charAt(0).toUpperCase() + domain.slice(1),
    kept: stats.kept || 0,
    rolledback: stats.rolledback || 0,
  }));

  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
      <h3 className="text-sm font-medium text-slate-300 mb-3">Mutations per Domain</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis dataKey="name" type="category" width={80} tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip content={<ChartTooltip />} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }}
            formatter={(v) => <span className="text-slate-300">{v}</span>} />
          <Bar dataKey="kept" name="Kept" fill={COLORS.green} radius={[0, 4, 4, 0]} stackId="a" />
          <Bar dataKey="rolledback" name="Rolled Back" fill={COLORS.orange} radius={[0, 4, 4, 0]} stackId="a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function InterestCard({ interest }) {
  const depthPct = (interest.depth / 10) * 100;
  const depthColor = interest.depth >= 7 ? COLORS.green : interest.depth >= 4 ? COLORS.cyan : COLORS.purple;

  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-700/50">
      <div className="flex items-start justify-between mb-2">
        <span className="text-sm font-medium text-white truncate">{interest.topic}</span>
        <span className="text-xs text-slate-500 ml-2 whitespace-nowrap">{interest.age_days}d</span>
      </div>
      <div className="mb-2">
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>Depth</span><span>{interest.depth}/10</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-2">
          <div className="h-2 rounded-full transition-all" style={{
            width: `${depthPct}%`, backgroundColor: depthColor,
          }} />
        </div>
      </div>
      <div className="mb-2">
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>Enthusiasm</span><span>{Math.round(interest.enthusiasm * 100)}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-2">
          <div className="h-2 rounded-full bg-yellow-500 transition-all"
            style={{ width: `${interest.enthusiasm * 100}%` }} />
        </div>
      </div>
      <div className="flex justify-between text-xs text-slate-500 mt-2">
        <span>{interest.sessions} sessions</span>
        <span>{interest.discoveries} discoveries</span>
        <span>{Math.round(interest.total_time_minutes)}min</span>
      </div>
    </div>
  );
}

function WatchdogObservation({ obs }) {
  const sourceColors = { chat: COLORS.cyan, activity: COLORS.purple, finding: COLORS.green };
  const sourceColor = sourceColors[obs.source] || COLORS.slate;
  const hasRegistered = !!obs.registered;
  const time = obs.timestamp ? new Date(obs.timestamp + 'Z').toLocaleTimeString('pt-PT', {
    hour: '2-digit', minute: '2-digit'
  }) : '';

  return (
    <div className={`flex items-start gap-3 p-2 rounded-lg ${hasRegistered ? 'bg-green-950/30 border border-green-800/30' : 'bg-slate-800/50'}`}>
      <div className="flex flex-col items-center gap-1 min-w-[52px]">
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
          style={{ backgroundColor: sourceColor + '22', color: sourceColor }}>
          {obs.source}
        </span>
        <span className="text-[10px] text-slate-600">{time}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-slate-400 truncate" title={obs.input_preview}>
          {obs.input_preview}
        </div>
        {obs.extracted_topics?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {obs.extracted_topics.map((topic, j) => (
              <span key={j} className={`text-[10px] px-1.5 py-0.5 rounded ${
                topic === obs.registered
                  ? 'bg-green-900/50 text-green-300 ring-1 ring-green-500/30'
                  : 'bg-slate-700/50 text-slate-400'
              }`}>
                {topic === obs.registered && '✓ '}{topic}
              </span>
            ))}
          </div>
        )}
        {obs.extracted_topics?.length === 0 && obs.rejected?.length > 0 && (
          <span className="text-[10px] text-slate-600 italic">
            {obs.rejected[0]}
          </span>
        )}
        {obs.rejected?.length > 0 && obs.extracted_topics?.length > 0 && (
          <div className="text-[10px] text-slate-600 mt-0.5">
            {obs.rejected.map((r, k) => <span key={k} className="mr-2">{r}</span>)}
          </div>
        )}
      </div>
      <span className="text-[10px] text-slate-600 whitespace-nowrap">#{obs.cycle_count}</span>
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
