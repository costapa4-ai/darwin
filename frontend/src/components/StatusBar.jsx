import { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function StatusBar() {
  const [status, setStatus] = useState({
    phase3Enabled: false,
    currentActivity: 'Idle',
    activeAgents: 0,
    isDreaming: false,
    lastUpdate: new Date()
  });
  const [phase3Status, setPhase3Status] = useState(null);

  useEffect(() => {
    // Fetch Phase 3 status
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${api.baseURL}/api/v1/phase3/status`);
        if (response.ok) {
          const data = await response.json();
          setPhase3Status(data);
          setStatus(prev => ({
            ...prev,
            phase3Enabled: data.phase3_enabled,
            lastUpdate: new Date()
          }));
        }
      } catch (error) {
        console.error('Failed to fetch Phase 3 status:', error);
      }
    };

    // Fetch dream status
    const fetchDreamStatus = async () => {
      try {
        const response = await fetch(`${api.baseURL}/api/v1/phase3/dreams/status`);
        if (response.ok) {
          const data = await response.json();
          setStatus(prev => ({
            ...prev,
            isDreaming: data.is_active || false,
            currentActivity: data.is_active ? 'Dreaming 💭' : 'Ready',
            lastUpdate: new Date()
          }));
        }
      } catch (error) {
        // Phase 3 might not be enabled
      }
    };

    // Fetch agent stats
    const fetchAgentStats = async () => {
      try {
        const response = await fetch(`${api.baseURL}/api/v1/phase3/agents/list`);
        if (response.ok) {
          const data = await response.json();
          setStatus(prev => ({
            ...prev,
            activeAgents: data.total || 0
          }));
        }
      } catch (error) {
        // Phase 3 might not be enabled
      }
    };

    fetchStatus();
    fetchDreamStatus();
    fetchAgentStats();

    // Refresh every 10 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchDreamStatus();
      fetchAgentStats();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const getActivityIcon = () => {
    if (status.isDreaming) return '💭';
    if (status.currentActivity === 'Evolving') return '🧬';
    if (status.currentActivity === 'Thinking') return '🤔';
    return '✨';
  };

  const getActivityColor = () => {
    if (status.isDreaming) return 'text-purple-400';
    if (status.currentActivity === 'Evolving') return 'text-green-400';
    if (status.currentActivity === 'Thinking') return 'text-yellow-400';
    return 'text-blue-400';
  };

  return (
    <div className="bg-gradient-to-r from-slate-800 to-slate-700 border-b border-slate-600 shadow-lg">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between flex-wrap gap-4">
          {/* Current Activity */}
          <div className="flex items-center gap-3">
            <span className="text-2xl">{getActivityIcon()}</span>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wide">Status</div>
              <div className={`text-lg font-semibold ${getActivityColor()}`}>
                {status.currentActivity}
              </div>
            </div>
          </div>

          {/* Phase 3 Features */}
          {status.phase3Enabled && (
            <div className="flex items-center gap-6">
              {/* Active Agents */}
              <div className="flex items-center gap-2">
                <span className="text-xl">🤖</span>
                <div>
                  <div className="text-xs text-slate-400">Agents</div>
                  <div className="text-sm font-semibold text-white">
                    {status.activeAgents} Active
                  </div>
                </div>
              </div>

              {/* Dream Mode Indicator */}
              {status.isDreaming && (
                <div className="flex items-center gap-2 bg-purple-900/30 px-3 py-1 rounded-full border border-purple-500/30">
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
                  <span className="text-sm text-purple-300 font-medium">Dream Mode</span>
                </div>
              )}

              {/* Features Badge */}
              {phase3Status?.features && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-400">Features:</span>
                  <div className="flex gap-1">
                    {phase3Status.features.multi_agent && (
                      <span className="text-xs bg-green-900/30 text-green-300 px-2 py-1 rounded border border-green-500/30">
                        Multi-Agent
                      </span>
                    )}
                    {phase3Status.features.dream_mode && (
                      <span className="text-xs bg-purple-900/30 text-purple-300 px-2 py-1 rounded border border-purple-500/30">
                        Dreams
                      </span>
                    )}
                    {phase3Status.features.code_poetry && (
                      <span className="text-xs bg-pink-900/30 text-pink-300 px-2 py-1 rounded border border-pink-500/30">
                        Poetry
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Last Update */}
          <div className="text-xs text-slate-500">
            Updated {status.lastUpdate.toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}
