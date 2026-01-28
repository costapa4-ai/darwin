import { useEffect, useState } from 'react';
import { getMetrics } from '../utils/api';

export default function MetricsPanel() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadMetrics = async () => {
    try {
      const data = await getMetrics();
      setMetrics(data);
    } catch (error) {
      console.error('Error loading metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
        <div className="text-center text-slate-400">Loading metrics...</div>
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  const { system, executions, performance } = metrics;

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      <h2 className="text-xl font-bold mb-4 text-green-400">📊 System Metrics</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Uptime"
          value={system?.uptime_formatted || '0s'}
          icon="⏱️"
        />
        <MetricCard
          title="Total Tasks"
          value={executions?.total || 0}
          icon="🎯"
        />
        <MetricCard
          title="Success Rate"
          value={`${executions?.success_rate?.toFixed(1) || 0}%`}
          icon="✅"
          color={executions?.success_rate > 70 ? 'text-green-400' : 'text-yellow-400'}
        />
        <MetricCard
          title="Avg Fitness"
          value={performance?.avg_fitness_score?.toFixed(1) || 0}
          icon="🏆"
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="bg-slate-700 rounded p-3">
          <div className="text-sm text-slate-400">Successful</div>
          <div className="text-2xl font-bold text-green-400">
            {executions?.successful || 0}
          </div>
        </div>
        <div className="bg-slate-700 rounded p-3">
          <div className="text-sm text-slate-400">Failed</div>
          <div className="text-2xl font-bold text-red-400">
            {executions?.failed || 0}
          </div>
        </div>
      </div>

      <div className="mt-4 bg-slate-700 rounded p-3">
        <div className="text-sm text-slate-400">Avg Execution Time</div>
        <div className="text-xl font-bold text-blue-400">
          {performance?.avg_execution_time?.toFixed(4) || 0}s
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon, color = 'text-white' }) {
  return (
    <div className="bg-slate-700 rounded p-3">
      <div className="text-sm text-slate-400 mb-1">{title}</div>
      <div className="flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        <span className={`text-xl font-bold ${color}`}>{value}</span>
      </div>
    </div>
  );
}
