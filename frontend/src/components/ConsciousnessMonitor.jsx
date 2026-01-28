import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function ConsciousnessMonitor() {
  const [status, setStatus] = useState(null);
  const [activities, setActivities] = useState([]);
  const [curiosities, setCuriosities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const statusRes = await fetch(`${API_BASE}/api/v1/consciousness/status`);
      const statusData = await statusRes.json();
      setStatus(statusData);

      const activitiesRes = await fetch(`${API_BASE}/api/v1/consciousness/wake-activities?limit=5`);
      const activitiesData = await activitiesRes.json();
      setActivities(activitiesData.activities || []);

      const curiositiesRes = await fetch(`${API_BASE}/api/v1/consciousness/curiosities?limit=3`);
      const curiositiesData = await curiositiesRes.json();
      setCuriosities(curiositiesData.curiosities || []);

      setLoading(false);
    } catch (error) {
      console.error('Error fetching consciousness data:', error);
      setLoading(false);
    }
  };

  if (loading || !status) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-xl font-bold mb-4 text-blue-400">🧬 Consciousness Engine</h2>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400"></div>
          <span className="ml-4 text-slate-300">Loading consciousness data...</span>
        </div>
      </div>
    );
  }

  const isAwake = status.state === 'wake';
  const progress = (status.elapsed_minutes / (isAwake ? 120 : 30)) * 100;

  const getActivityIcon = (type) => {
    const icons = {
      'code_optimization': '⚡',
      'tool_creation': '🛠️',
      'idea_implementation': '💡',
      'curiosity_share': '🎯',
      'self_improvement': '🔬'
    };
    return icons[type] || '🧬';
  };

  const getActivityColor = (type) => {
    const colors = {
      'code_optimization': 'border-green-500',
      'tool_creation': 'border-orange-500',
      'idea_implementation': 'border-blue-500',
      'curiosity_share': 'border-purple-500',
      'self_improvement': 'border-red-500'
    };
    return colors[type] || 'border-slate-500';
  };

  return (
    <div className="bg-slate-800 rounded-lg shadow-lg overflow-hidden">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6">
        <div className="flex items-center gap-3">
          <span className="text-4xl">🧬</span>
          <div>
            <h2 className="text-2xl font-bold text-white">Darwin Consciousness</h2>
            <p className="text-blue-100">Autonomous Wake/Sleep Cycles</p>
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className={`rounded-lg p-4 mb-6 ${isAwake ? 'bg-orange-900/30 border border-orange-500/50' : 'bg-blue-900/30 border border-blue-500/50'}`}>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <span className="text-4xl">{isAwake ? '🌅' : '😴'}</span>
              <div>
                <h3 className="text-2xl font-bold text-white uppercase">{isAwake ? 'Wake Mode' : 'Sleep Mode'}</h3>
                <p className="text-sm text-slate-300">
                  {isAwake ? 'Active Development & Creativity' : 'Deep Research & Learning'}
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-slate-300">Elapsed: {Math.round(status.elapsed_minutes)} min</div>
              <div className="text-sm text-slate-300">Remaining: {Math.round(status.remaining_minutes)} min</div>
            </div>
          </div>

          <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full transition-all duration-1000 ${isAwake ? 'bg-gradient-to-r from-orange-500 to-yellow-500' : 'bg-gradient-to-r from-blue-500 to-purple-500'}`}
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-700 rounded-lg p-4">
            <div className="text-3xl font-bold text-blue-400">{status.total_activities}</div>
            <div className="text-sm text-slate-400">Activities</div>
          </div>
          <div className="bg-slate-700 rounded-lg p-4">
            <div className="text-3xl font-bold text-purple-400">{status.total_discoveries}</div>
            <div className="text-sm text-slate-400">Discoveries</div>
          </div>
          <div className="bg-slate-700 rounded-lg p-4">
            <div className="text-3xl font-bold text-orange-400">{status.wake_cycles_completed}</div>
            <div className="text-sm text-slate-400">Wake Cycles</div>
          </div>
          <div className="bg-slate-700 rounded-lg p-4">
            <div className="text-3xl font-bold text-blue-400">{status.sleep_cycles_completed}</div>
            <div className="text-sm text-slate-400">Sleep Cycles</div>
          </div>
        </div>

        <div className="mb-6">
          <h3 className="text-xl font-bold mb-3 text-orange-400 flex items-center gap-2">
            <span>🌅</span> Recent Wake Activities
          </h3>
          {activities.length === 0 ? (
            <div className="bg-slate-700 rounded-lg p-4 text-center text-slate-400">No activities yet...</div>
          ) : (
            <div className="space-y-3">
              {activities.map((activity, idx) => (
                <div key={idx} className={`bg-slate-700 rounded-lg p-4 border-l-4 ${getActivityColor(activity.type)}`}>
                  <div className="flex items-start gap-2 mb-2">
                    <span className="text-2xl">{getActivityIcon(activity.type)}</span>
                    <div className="flex-1">
                      <h4 className="font-bold text-white">{activity.description}</h4>
                      <div className="text-xs text-slate-400 mt-1">
                        {activity.type.replace('_', ' ').toUpperCase()}
                      </div>
                    </div>
                  </div>

                  {activity.insights && activity.insights.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {activity.insights.map((insight, i) => (
                        <div key={i} className="text-sm text-slate-300 ml-8">• {insight}</div>
                      ))}
                    </div>
                  )}

                  {activity.result && (
                    <div className="mt-2 text-xs text-slate-400 ml-8">
                      Result: {JSON.stringify(activity.result)}
                    </div>
                  )}

                  <div className="mt-2 text-xs text-slate-500 ml-8">
                    {new Date(activity.started_at).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {curiosities.length > 0 && (
          <div>
            <h3 className="text-xl font-bold mb-3 text-purple-400 flex items-center gap-2">
              <span>📚</span> Curiosity Moments
            </h3>
            <div className="space-y-3">
              {curiosities.map((curiosity, idx) => (
                <div key={idx} className="bg-gradient-to-r from-purple-900/30 to-pink-900/30 border border-purple-500/50 rounded-lg p-4">
                  <h4 className="font-bold text-purple-300 mb-2">📚 {curiosity.topic}</h4>
                  <p className="text-sm text-slate-300 mb-2">💡 {curiosity.fact}</p>
                  <p className="text-sm text-slate-400 italic">✨ Why it matters: {curiosity.significance}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ConsciousnessMonitor;
