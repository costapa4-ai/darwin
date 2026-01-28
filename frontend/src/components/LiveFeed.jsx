import { useEffect, useRef } from 'react';

export default function LiveFeed({ events }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const getEventIcon = (type) => {
    switch (type) {
      case 'task_created': return '🎯';
      case 'generation_started': return '🧬';
      case 'solution_executed': return '⚡';
      case 'best_solution_found': return '🏆';
      case 'evolution_complete': return '✅';
      case 'task_failed': return '❌';
      case 'agent_selected': return '🤖';
      case 'collaboration_started': return '👥';
      case 'dream_started': return '💭';
      default: return '📡';
    }
  };

  const getEventColor = (type) => {
    switch (type) {
      case 'task_created': return 'border-blue-500 bg-blue-900/20';
      case 'generation_started': return 'border-purple-500 bg-purple-900/20';
      case 'solution_executed': return 'border-yellow-500 bg-yellow-900/20';
      case 'best_solution_found': return 'border-green-500 bg-green-900/20';
      case 'evolution_complete': return 'border-green-400 bg-green-900/30';
      case 'task_failed': return 'border-red-500 bg-red-900/20';
      case 'agent_selected': return 'border-cyan-500 bg-cyan-900/20';
      case 'collaboration_started': return 'border-pink-500 bg-pink-900/20';
      case 'dream_started': return 'border-purple-400 bg-purple-900/30';
      default: return 'border-gray-500 bg-gray-900/20';
    }
  };

  const getHumanFriendlyMessage = (event) => {
    const { type, data } = event;

    switch (type) {
      case 'task_created':
        return `🎯 New task: "${data?.description || 'Unknown task'}"`;

      case 'generation_started':
        return `🧬 Starting generation ${data?.generation || '?'} - Creating ${data?.population_size || 3} solutions`;

      case 'solution_executed':
        const success = data?.success ? '✓' : '✗';
        const fitness = data?.fitness_score?.toFixed(1) || '0';
        return `⚡ Solution ${success} - Fitness: ${fitness}/100 ${data?.execution_time ? `(${(data.execution_time * 1000).toFixed(0)}ms)` : ''}`;

      case 'best_solution_found':
        return `🏆 Best solution so far! Fitness: ${data?.fitness_score?.toFixed(1) || '0'}/100`;

      case 'evolution_complete':
        return `✅ Evolution complete! Best fitness: ${data?.best_fitness?.toFixed(1) || '0'}/100 after ${data?.generations || '?'} generations`;

      case 'task_failed':
        return `❌ Task failed: ${data?.error || 'Unknown error'}`;

      case 'agent_selected':
        return `🤖 Agent "${data?.agent_name || 'Unknown'}" selected for this task`;

      case 'collaboration_started':
        return `👥 ${data?.num_agents || 3} agents collaborating on solution`;

      case 'dream_started':
        return `💭 Darwin entered dream mode - exploring ${data?.dream_type || 'unknown'} autonomously`;

      default:
        return `📡 ${type.replace(/_/g, ' ')}`;
    }
  };

  const getDetailedInfo = (event) => {
    const { data } = event;
    if (!data || typeof data !== 'object') return null;

    const details = [];

    if (data.task_description) details.push(`Task: ${data.task_description}`);
    if (data.code) details.push(`Code generated: ${data.code.length} characters`);
    if (data.output) details.push(`Output: ${data.output}`);
    if (data.error) details.push(`Error: ${data.error}`);
    if (data.memory_used) details.push(`Memory: ${(data.memory_used / 1024 / 1024).toFixed(2)} MB`);

    return details.length > 0 ? details : null;
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-green-400">📡 Live Activity Feed</h2>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span className="text-sm text-slate-400">{events.length} events</span>
        </div>
      </div>

      <div className="h-[600px] overflow-y-auto space-y-3 pr-2">
        {events.length === 0 ? (
          <div className="text-center text-slate-400 py-12">
            <div className="text-6xl mb-4">🌟</div>
            <div className="text-lg">Waiting for Darwin to start working...</div>
            <div className="text-sm mt-2">Create a task to see evolution in action!</div>
          </div>
        ) : (
          events.map((event, idx) => {
            const details = getDetailedInfo(event);
            return (
              <div
                key={event.id || idx}
                className={`rounded-lg p-4 border-l-4 ${getEventColor(event.type)} transition-all hover:scale-[1.01]`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl flex-shrink-0">{getEventIcon(event.type)}</span>
                  <div className="flex-1 min-w-0">
                    {/* Main message */}
                    <div className="font-medium text-white text-base mb-1">
                      {getHumanFriendlyMessage(event)}
                    </div>

                    {/* Timestamp */}
                    <div className="text-xs text-slate-500 mb-2">
                      {new Date(event.timestamp || Date.now()).toLocaleTimeString()}
                    </div>

                    {/* Detailed info */}
                    {details && details.length > 0 && (
                      <div className="mt-2 text-sm text-slate-300 space-y-1 bg-slate-900/50 rounded p-2">
                        {details.map((detail, i) => (
                          <div key={i} className="truncate">• {detail}</div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>

      {/* Scroll indicator */}
      {events.length > 5 && (
        <div className="mt-3 text-center text-xs text-slate-500">
          Scroll up to see older events
        </div>
      )}
    </div>
  );
}
