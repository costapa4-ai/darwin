import { useState, useEffect } from 'react';
import ApprovalsPanel from './ApprovalsPanel';
import FindingsInbox from './FindingsInbox';
import LanguageEvolutionPanel from './LanguageEvolutionPanel';
import MonitorPanel from './MonitorPanel';
import { API_BASE } from '../utils/config';

export default function NewDashboard({ onNavigate }) {
  const [status, setStatus] = useState(null);
  const [allEvents, setAllEvents] = useState([]);
  const [pendingChanges, setPendingChanges] = useState(0);
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [sending, setSending] = useState(false);
  const [showApprovals, setShowApprovals] = useState(false);
  const [showDiscoveries, setShowDiscoveries] = useState(false);
  const [discoveries, setDiscoveries] = useState([]);
  const [showCosts, setShowCosts] = useState(false);
  const [costData, setCostData] = useState(null);
  const [showFindings, setShowFindings] = useState(false);
  const [findingsCount, setFindingsCount] = useState(0);
  const [showLanguageEvolution, setShowLanguageEvolution] = useState(false);
  const [showMonitor, setShowMonitor] = useState(false);
  const [showRouting, setShowRouting] = useState(false);
  const [routingData, setRoutingData] = useState(null);

  useEffect(() => {
    fetchData();
    fetchChatHistory();
    const interval = setInterval(() => {
      fetchData();
      fetchChatHistory();
    }, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      // Fetch consciousness status
      const statusRes = await fetch(`${API_BASE}/api/v1/consciousness/status`);
      const statusData = await statusRes.json();
      setStatus(statusData);

      // Fetch unified consciousness stream (Global Workspace)
      const streamRes = await fetch(`${API_BASE}/api/v1/consciousness/stream?limit=50`);
      const streamData = await streamRes.json();
      const streamEvents = (streamData.events || []).map(e => ({
        ...e,
        eventType: e.event_type || e.eventType || 'activity',
        timestamp: e.timestamp,
        // Map stream fields to legacy field names for rendering compatibility
        description: e.title || e.description || e.content || '',
        type: e.metadata?.type || e.event_type || '',
        topic: e.title || e.topic || '',
        fact: e.content || e.fact || '',
        significance: e.metadata?.significance || '',
        insights: e.metadata?.insights || [],
        exploration_details: e.metadata?.exploration_details || null,
      }));
      setAllEvents(streamEvents);

      // Fetch pending changes from approval queue with timeout
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout

        const approvalsRes = await fetch(`${API_BASE}/api/v1/consciousness/approvals/pending`, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        const approvalsData = await approvalsRes.json();
        // Use count directly from API, fallback to pending_changes length
        const count = approvalsData.count !== undefined
          ? approvalsData.count
          : (approvalsData.pending_changes || []).length;
        setPendingChanges(count);
      } catch (error) {
        if (error.name === 'AbortError') {
          console.warn('Pending changes request timed out');
        } else {
          console.error('Error fetching pending changes:', error);
        }
        setPendingChanges(0); // Safe fallback
      }

      // Fetch findings count
      try {
        const findingsRes = await fetch(`${API_BASE}/api/v1/findings/count`);
        const findingsData = await findingsRes.json();
        setFindingsCount(findingsData.unread_count || 0);
      } catch (error) {
        console.error('Error fetching findings count:', error);
        setFindingsCount(0);
      }

    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/consciousness/chat/history?limit=50`);
      const data = await res.json();
      setChatHistory(data.messages || []);
    } catch (error) {
      console.error('Error fetching chat history:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!message.trim() || sending) return;

    setSending(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/consciousness/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message.trim() })
      });

      if (res.ok) {
        const darwin_response = await res.json();
        setMessage('');
        // Fetch updated chat history
        await fetchChatHistory();
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setSending(false);
    }
  };

  const fetchDiscoveries = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/consciousness/discoveries?limit=100`);
      const data = await res.json();
      setDiscoveries(data.discoveries || []);
    } catch (error) {
      console.error('Error fetching discoveries:', error);
    }
  };

  const handleDiscoveriesClick = async () => {
    await fetchDiscoveries();
    setShowDiscoveries(true);
  };

  const fetchCosts = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/costs/summary`);
      const data = await res.json();
      setCostData(data);
    } catch (error) {
      console.error('Error fetching costs:', error);
    }
  };

  const handleCostsClick = async () => {
    await fetchCosts();
    setShowCosts(true);
  };

  const fetchRouting = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/observatory/ai-routing`);
      const data = await res.json();
      setRoutingData(data);
    } catch (error) {
      console.error('Error fetching routing:', error);
    }
  };

  const handleRoutingClick = async () => {
    await fetchRouting();
    setShowRouting(true);
  };

  const handleExportData = (dataset = 'all', format = 'json') => {
    const url = dataset === 'all'
      ? `${API_BASE}/api/v1/export/all`
      : `${API_BASE}/api/v1/export/${dataset}?format=${format}`;
    window.open(url, '_blank');
  };

  const isAwake = status?.state === 'wake';
  const progress = status ? (status.elapsed_minutes / (isAwake ? 120 : 30)) * 100 : 0;

  const getEventIcon = (event) => {
    if (event.eventType === 'activity') {
      const icons = {
        'code_optimization': '⚡',
        'tool_creation': '🛠️',
        'idea_implementation': '💡',
        'curiosity_share': '🎯',
        'self_improvement': '🔬'
      };
      return icons[event.type] || '⚡';
    } else if (event.eventType === 'dream') {
      return '💭';
    } else if (event.eventType === 'curiosity') {
      return '📚';
    } else if (event.eventType === 'mood_change') {
      return '🎭';
    } else if (event.eventType === 'state_transition') {
      return '🔄';
    } else if (event.eventType === 'discovery') {
      return '💡';
    } else if (event.eventType === 'genome_mutation') {
      return '🧬';
    } else if (event.eventType === 'chat_message') {
      return '💬';
    } else if (event.eventType === 'expedition') {
      return '🗺️';
    } else if (event.eventType === 'thought') {
      return '🤔';
    } else if (event.eventType === 'intention') {
      return '🎯';
    } else if (event.eventType === 'memory_recall') {
      return '🧠';
    } else if (event.eventType === 'inner_voice') {
      return '🗣️';
    }
    return '•';
  };

  const getEventColor = (event) => {
    if (event.eventType === 'activity') {
      const colors = {
        'code_optimization': 'border-green-500 bg-green-900/20',
        'tool_creation': 'border-orange-500 bg-orange-900/20',
        'idea_implementation': 'border-blue-500 bg-blue-900/20',
        'curiosity_share': 'border-purple-500 bg-purple-900/20',
        'self_improvement': 'border-red-500 bg-red-900/20'
      };
      return colors[event.type] || 'border-slate-500 bg-slate-900/20';
    } else if (event.eventType === 'dream') {
      return 'border-blue-400 bg-blue-900/20';
    } else if (event.eventType === 'curiosity') {
      return 'border-purple-400 bg-purple-900/20';
    } else if (event.eventType === 'mood_change') {
      return 'border-yellow-400 bg-yellow-900/20';
    } else if (event.eventType === 'state_transition') {
      return 'border-cyan-400 bg-cyan-900/20';
    } else if (event.eventType === 'discovery') {
      return 'border-amber-400 bg-amber-900/20';
    } else if (event.eventType === 'genome_mutation') {
      return 'border-pink-400 bg-pink-900/20';
    } else if (event.eventType === 'chat_message') {
      return 'border-emerald-400 bg-emerald-900/20';
    } else if (event.eventType === 'expedition') {
      return 'border-indigo-400 bg-indigo-900/20';
    } else if (event.eventType === 'thought') {
      return 'border-gray-400 bg-gray-900/20';
    } else if (event.eventType === 'memory_recall') {
      return 'border-teal-400 bg-teal-900/20';
    } else if (event.eventType === 'inner_voice') {
      return 'border-orange-400 bg-orange-900/20';
    }
    return 'border-slate-500 bg-slate-900/20';
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' });
  };

  return (
    <div className="h-screen bg-slate-950 flex flex-col overflow-hidden">

      {/* ==================== TOP NAVIGATION BAR ==================== */}
      <nav className="bg-slate-900 border-b border-slate-700 px-4 flex items-center justify-between flex-shrink-0 h-10">
        {/* Left: Logo + State */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-lg">🧬</span>
            <span className="text-sm font-bold text-white">Darwin</span>
            <span className="text-xs text-slate-500">v4.0</span>
          </div>
          {status && (
            <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
              isAwake
                ? 'bg-orange-900/40 text-orange-300 border border-orange-700/50'
                : 'bg-blue-900/40 text-blue-300 border border-blue-700/50'
            }`}>
              <span>{isAwake ? '🌅' : '😴'}</span>
              {isAwake ? 'Awake' : 'Sleep'} {Math.round(status.elapsed_minutes)}m
            </div>
          )}
        </div>

        {/* Center: Page Navigation */}
        <div className="flex items-center gap-1">
          <button
            className="px-3 py-1 rounded text-sm font-medium text-white bg-white/10 border-b-2 border-blue-500"
          >
            Dashboard
          </button>
          <button
            onClick={() => onNavigate && onNavigate('genome')}
            className="px-3 py-1 rounded text-sm font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            🧬 Genome
          </button>
          <button
            onClick={() => onNavigate && onNavigate('core-values')}
            className="px-3 py-1 rounded text-sm font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            🔮 Values
          </button>
          <button
            onClick={() => onNavigate && onNavigate('observatory')}
            className="px-3 py-1 rounded text-sm font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            📊 Observatory
          </button>
        </div>

        {/* Right: Action Buttons */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleCostsClick}
            className="px-2 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-1"
            title="API Cost Summary"
          >
            💰 Costs
          </button>
          <button
            onClick={handleRoutingClick}
            className="px-2 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-1"
            title="AI Model Routing Stats"
          >
            📈 Routing
          </button>
          <button
            onClick={() => setShowMonitor(true)}
            className="px-2 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-1"
            title="Activity Monitor"
          >
            📊 Monitor
          </button>
          <button
            onClick={() => setShowLanguageEvolution(true)}
            className="px-2 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-1"
            title="Language Evolution"
          >
            🗣️ Lang
          </button>
          <button
            onClick={() => handleExportData('all')}
            className="px-2 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-1"
            title="Download all data as JSON"
          >
            📥 Export
          </button>
          <button
            onClick={() => {
              const currentHost = window.location.hostname;
              window.location.href = `http://${currentHost}:3051`;
            }}
            className="px-2 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-1"
            title="3D Brain Visualization"
          >
            🧠 3D
          </button>
        </div>
      </nav>

      {/* ==================== MAIN CONTENT (3-column) ==================== */}
      <div className="flex-1 flex overflow-hidden">

      {/* LEFT SIDEBAR - Status & Chat */}
      <div className="w-96 bg-slate-900 border-r border-slate-700 flex flex-col">

        {/* Current State */}
        {status && (
          <div className={`p-2 border-b border-slate-700 ${isAwake ? 'bg-orange-900/30' : 'bg-blue-900/30'}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">{isAwake ? '🌅' : '😴'}</span>
              <div className="flex-1">
                <div className="font-bold text-white text-base uppercase">{isAwake ? 'Acordado' : 'A Dormir'}</div>
                <div className="text-xs text-slate-300">
                  {Math.round(status.elapsed_minutes)}min / {isAwake ? '120min' : '30min'}
                </div>
              </div>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-1.5">
              <div
                className={`h-full rounded-full transition-all ${isAwake ? 'bg-gradient-to-r from-orange-500 to-yellow-500' : 'bg-gradient-to-r from-blue-500 to-purple-500'}`}
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Metrics */}
        <div className="grid grid-cols-3 gap-1.5 p-2 border-b border-slate-700">
          <div className="bg-slate-800 rounded-lg p-1.5">
            <div className="text-xl font-bold text-blue-400">{status?.total_activities || 0}</div>
            <div className="text-xs text-slate-400">Atividades</div>
          </div>
          <div
            className="bg-slate-800 rounded-lg p-1.5 cursor-pointer hover:bg-slate-700 transition-colors"
            onClick={handleDiscoveriesClick}
            title="Clique para ver lista de descobertas"
          >
            <div className="text-xl font-bold text-purple-400">{status?.total_discoveries || 0}</div>
            <div className="text-xs text-slate-400">Descobertas 🔍</div>
          </div>
          <div className="bg-slate-800 rounded-lg p-1.5">
            <div className="text-xl font-bold text-orange-400">{status?.wake_cycles_completed || 0}</div>
            <div className="text-xs text-slate-400">Ciclos Wake</div>
          </div>
        </div>

        {/* Findings Indicator */}
        {findingsCount > 0 && (
          <div
            className="mx-2 my-1 bg-purple-900/30 border border-purple-500/50 rounded-lg p-1.5 cursor-pointer hover:bg-purple-900/40 transition-colors"
            onClick={() => setShowFindings(true)}
          >
            <div className="flex items-center gap-1.5">
              <span className="text-xl">📬</span>
              <div className="flex-1">
                <div className="font-bold text-purple-300 text-xs">{findingsCount} Findings</div>
              </div>
              <span className="text-base text-purple-300">▶</span>
            </div>
          </div>
        )}

        {/* Pending Changes Indicator - Ultra Compacto */}
        {pendingChanges > 0 && (
          <div
            className="mx-2 my-1 bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-1.5 cursor-pointer hover:bg-yellow-900/40 transition-colors"
            onClick={() => setShowApprovals(!showApprovals)}
          >
            <div className="flex items-center gap-1.5">
              <span className="text-xl">⚠️</span>
              <div className="flex-1">
                <div className="font-bold text-yellow-300 text-xs">{pendingChanges} Mudanças</div>
              </div>
              <span className="text-base text-yellow-300">{showApprovals ? '▼' : '▶'}</span>
            </div>
          </div>
        )}

        {/* Chat with Darwin - Ultra Compacto */}
        <div className="flex-1 flex flex-col p-2 min-h-0">
          <h3 className="font-bold text-white text-sm mb-1 flex items-center gap-1">
            <span className="text-base">💬</span> Chat
          </h3>
          <div className="flex-1 bg-slate-800 rounded-lg p-2 mb-1 overflow-y-auto space-y-1 min-h-0">
            {chatHistory.length === 0 ? (
              <p className="text-xs text-slate-400 italic">Envia mensagem...</p>
            ) : (
              chatHistory.map((msg, idx) => (
                <div
                  key={msg.id || `${msg.timestamp || idx}-${msg.role}-${idx}`}
                  className={`p-1.5 rounded ${
                    msg.role === 'user'
                      ? 'bg-blue-900/30 text-blue-100 ml-2'
                      : 'bg-purple-900/30 text-purple-100 mr-2'
                  }`}
                >
                  <div className="font-semibold text-xs mb-0.5">
                    {msg.role === 'user' ? 'Tu' : '🧬'}
                    {msg.state && (
                      <span className="ml-1 opacity-60 text-xs">
                        {msg.state === 'wake' ? '🌅' : '😴'}
                      </span>
                    )}
                  </div>
                  <div className="leading-tight text-xs">{msg.content}</div>
                </div>
              ))
            )}
          </div>
          <div className="flex gap-1">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !sending && handleSendMessage()}
              placeholder="Escreve..."
              disabled={sending}
              className="flex-1 bg-slate-800 text-white px-2 py-1.5 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSendMessage}
              disabled={sending}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
            >
              {sending ? '...' : '📤'}
            </button>
          </div>
        </div>
      </div>

      {/* CENTER - Activity Feed */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Feed Header - Compacto para 1080p */}
        <div className="bg-slate-900 border-b border-slate-700 p-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <span className="animate-pulse text-green-400 text-xl">●</span>
                Feed em Direto
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                {allEvents.length > 0 ? (
                  <>{allEvents.length} eventos {allEvents.length === 50 ? '(máx)' : ''}</>
                ) : (
                  'Aguardando...'
                )}
              </p>
            </div>
            {allEvents.length >= 50 && (
              <div className="bg-yellow-900/30 border border-yellow-500/50 rounded-lg px-2 py-1">
                <div className="text-xs text-yellow-300 font-semibold">Limite: 50</div>
              </div>
            )}
          </div>
        </div>

        {/* Event Feed - Ajustado para 1080p */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 space-y-3">
          {allEvents.length === 0 ? (
            <div className="text-center text-slate-500 py-8">
              <span className="text-5xl block mb-3">🧬</span>
              <p className="text-lg">Aguardando...</p>
            </div>
          ) : (
            allEvents.map((event, idx) => (
              <div
                key={`${event.eventType}-${idx}`}
                className={`border-l-4 rounded-lg p-3 ${getEventColor(event)} backdrop-blur-sm`}
              >
                {/* Event Header */}
                <div className="flex items-start gap-2 mb-2">
                  <span className="text-3xl flex-shrink-0">{getEventIcon(event)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-white text-lg leading-tight break-words">
                      {event.title || event.description || event.topic || event.content || ''}
                    </div>
                    {(event.eventType === 'activity' || event.event_type) && event.type && (
                      <div className="text-xs text-slate-400 uppercase font-semibold mt-1">
                        {(event.eventType || event.event_type)?.replace('_', ' ')}
                      </div>
                    )}
                    {event.content && event.content !== event.title && event.eventType !== 'chat_message' && (
                      <div className="text-xs text-slate-400 mt-1 break-words">
                        {event.content.length > 300 ? event.content.slice(0, 300) + '...' : event.content}
                      </div>
                    )}
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-xs text-slate-400">{formatDate(event.timestamp)}</div>
                    <div className="text-sm font-mono text-slate-300 font-semibold">{formatTime(event.timestamp)}</div>
                  </div>
                </div>

                {/* Event Content */}
                <div className="ml-10">
                  {/* Activity insights */}
                  {event.eventType === 'activity' && event.insights && event.insights.length > 0 && (
                    <div className="space-y-1 mb-2">
                      {event.insights.slice(0, 3).map((insight, i) => (
                        <div key={i} className="text-sm text-slate-300 leading-snug">• {insight}</div>
                      ))}
                      {event.insights.length > 3 && (
                        <div className="text-xs text-slate-500 italic">... +{event.insights.length - 3}</div>
                      )}
                    </div>
                  )}

                  {/* Activity result */}
                  {event.eventType === 'activity' && event.result && (
                    <div className="text-xs text-slate-400 bg-slate-800/50 rounded px-2 py-1 inline-block">
                      {JSON.stringify(event.result)}
                    </div>
                  )}

                  {/* Dream insights */}
                  {event.eventType === 'dream' && event.insights && event.insights.length > 0 && (
                    <div className="space-y-1 mb-2">
                      {event.insights.slice(0, 5).map((insight, i) => (
                        <div key={i} className="text-sm text-slate-300 leading-snug flex gap-1.5">
                          <span className="text-blue-400 flex-shrink-0">•</span>
                          <span>{insight}</span>
                        </div>
                      ))}
                      {event.insights.length > 5 && (
                        <div className="text-xs text-slate-500 italic ml-3.5">... +{event.insights.length - 5} mais insights</div>
                      )}
                    </div>
                  )}

                  {/* Dream exploration details */}
                  {event.eventType === 'dream' && event.exploration_details && (
                    <div className="mt-2 p-2 bg-slate-800/50 rounded border border-slate-700">
                      <div className="text-xs font-bold text-slate-400 uppercase mb-1">Explorado:</div>
                      {event.exploration_details.type === 'web' && (
                        <div className="space-y-1">
                          {event.exploration_details.url && (
                            <div className="text-xs text-blue-300 break-all">
                              🌐 <a href={event.exploration_details.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                                {event.exploration_details.url}
                              </a>
                            </div>
                          )}
                          {event.exploration_details.urls_visited && event.exploration_details.urls_visited.length > 1 && (
                            <div className="text-xs text-slate-400">
                              + {event.exploration_details.urls_visited.length - 1} páginas adicionais
                            </div>
                          )}
                          {event.exploration_details.knowledge_items && (
                            <div className="text-xs text-green-300">
                              💡 {event.exploration_details.knowledge_items} itens de conhecimento extraídos
                            </div>
                          )}
                        </div>
                      )}
                      {event.exploration_details.type === 'repository' && (
                        <div className="space-y-2">
                          {event.exploration_details.repository && (
                            <div className="text-xs text-blue-300 break-all">
                              📦 <a href={event.exploration_details.url} target="_blank" rel="noopener noreferrer" className="hover:underline font-semibold">
                                {event.exploration_details.repository}
                              </a>
                            </div>
                          )}
                          {event.exploration_details.insights_count && (
                            <div className="text-xs text-green-300">
                              💡 {event.exploration_details.insights_count} insights descobertos
                            </div>
                          )}
                          {event.exploration_details.patterns && event.exploration_details.patterns.length > 0 && (
                            <div className="mt-2 p-2 bg-slate-900/70 rounded border-l-2 border-purple-500">
                              <div className="text-xs font-bold text-purple-300 uppercase mb-1.5">🔍 Padrões Arquiteturais:</div>
                              <div className="space-y-1.5">
                                {event.exploration_details.patterns.slice(0, 3).map((pattern, pi) => (
                                  <div key={pi} className="text-xs text-slate-200 leading-relaxed pl-2 border-l border-purple-500/30">
                                    {pattern.length > 200 ? pattern.substring(0, 200) + '...' : pattern}
                                  </div>
                                ))}
                                {event.exploration_details.patterns.length > 3 && (
                                  <div className="text-xs text-slate-500 italic pl-2">
                                    ... e mais {event.exploration_details.patterns.length - 3} padrões
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                      {event.exploration_details.type === 'documentation' && (
                        <div className="space-y-1">
                          {event.exploration_details.file && (
                            <div className="text-xs text-green-300">
                              📚 {event.exploration_details.file}
                            </div>
                          )}
                          {event.exploration_details.source && (
                            <div className="text-xs text-slate-400">
                              Fonte: {event.exploration_details.source}
                            </div>
                          )}
                        </div>
                      )}
                      {event.exploration_details.type === 'experiment' && (
                        <div className="space-y-1">
                          {event.exploration_details.experiment && (
                            <div className="text-xs text-orange-300">
                              🧪 {event.exploration_details.experiment}
                            </div>
                          )}
                          {event.exploration_details.outcome && (
                            <div className="text-xs text-green-300">
                              ✅ {event.exploration_details.outcome}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Curiosity fact */}
                  {event.eventType === 'curiosity' && (
                    <div>
                      <p className="text-sm text-slate-300 mb-2 leading-snug">💡 {event.fact}</p>
                      <p className="text-xs text-slate-400 italic leading-snug">✨ {event.significance}</p>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Approvals Panel (Modal) */}
      <ApprovalsPanel
        isOpen={showApprovals}
        onClose={() => {
          setShowApprovals(false);
          fetchData(); // Refresh to update pending count
        }}
      />

      {/* Findings Inbox (Modal) */}
      <FindingsInbox
        isOpen={showFindings}
        onClose={() => {
          setShowFindings(false);
          fetchData(); // Refresh to update findings count
        }}
      />

      {/* Language Evolution Panel (Modal) */}
      <LanguageEvolutionPanel
        isOpen={showLanguageEvolution}
        onClose={() => setShowLanguageEvolution(false)}
      />

      {/* Monitor Panel */}
      <MonitorPanel
        isOpen={showMonitor}
        onClose={() => setShowMonitor(false)}
      />

      {/* Discoveries Modal */}
      {showDiscoveries && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg shadow-2xl border border-slate-700 w-full max-w-4xl h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-4 rounded-t-lg flex justify-between items-center flex-shrink-0">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <span>🔍</span> Descobertas do Darwin
              </h2>
              <button
                onClick={() => setShowDiscoveries(false)}
                className="text-white hover:bg-white/20 rounded-lg px-3 py-1 text-xl transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Body - Scrollable */}
            <div className="flex-1 overflow-y-auto p-4 min-h-0">
              {discoveries.length === 0 ? (
                <div className="text-center py-16">
                  <span className="text-7xl block mb-5">🔬</span>
                  <p className="text-xl text-slate-400">Nenhuma descoberta ainda...</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {discoveries.map((discovery, idx) => {
                    const discoveryKey = discovery.id || `${discovery.timestamp}-${discovery.type}-${idx}`;
                    const typeColors = {
                      'dream_insight': 'border-blue-500 bg-blue-900/20',
                      'code_implementation': 'border-green-500 bg-green-900/20',
                      'tool_creation': 'border-orange-500 bg-orange-900/20'
                    };
                    const typeIcons = {
                      'dream_insight': '💭',
                      'code_implementation': '⚡',
                      'tool_creation': '🛠️'
                    };
                    const typeLabels = {
                      'dream_insight': 'Insight de Pesquisa',
                      'code_implementation': 'Implementação de Código',
                      'tool_creation': 'Criação de Ferramenta'
                    };

                    return (
                      <div
                        key={discoveryKey}
                        className={`border-l-4 rounded-lg p-5 ${typeColors[discovery.type] || 'border-slate-500 bg-slate-800'}`}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <span className="text-3xl">{typeIcons[discovery.type] || '🔬'}</span>
                            <div>
                              <h3 className="text-xl font-bold text-white">{discovery.title}</h3>
                              <div className="text-sm text-slate-400 uppercase font-semibold mt-1">
                                {typeLabels[discovery.type] || discovery.type}
                                {discovery.implemented && (
                                  <span className="ml-2 text-green-400">✅ Implementado</span>
                                )}
                                {!discovery.implemented && (
                                  <span className="ml-2 text-yellow-400">📚 Pesquisa</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="text-sm text-slate-400">
                            {new Date(discovery.timestamp).toLocaleString('pt-PT')}
                          </div>
                        </div>

                        {/* Insights */}
                        {discovery.insights && discovery.insights.length > 0 && (
                          <div className="ml-12 space-y-2">
                            {discovery.insights.slice(0, 5).map((insight, i) => (
                              <div key={i} className="text-base text-slate-300 leading-relaxed">
                                • {insight}
                              </div>
                            ))}
                            {discovery.insights.length > 5 && (
                              <div className="text-sm text-slate-500 italic">
                                ... e mais {discovery.insights.length - 5} insights
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="bg-slate-800 p-4 rounded-b-lg border-t border-slate-700 flex-shrink-0">
              <div className="flex justify-between items-center">
                <div className="text-slate-400 text-base">
                  Total: <span className="text-white font-bold">{discoveries.length}</span>
                </div>
                <button
                  onClick={() => setShowDiscoveries(false)}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-5 py-2 rounded-lg text-base transition-colors font-semibold"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cost Modal */}
      {showCosts && costData && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg shadow-2xl border border-slate-700 w-full max-w-lg">
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-4 rounded-t-lg flex justify-between items-center">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <span>💰</span> Custos de API
              </h2>
              <button
                onClick={() => setShowCosts(false)}
                className="text-white hover:bg-white/20 rounded-lg px-3 py-1 text-xl transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-4">
              {/* Estimates */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-sm font-bold text-slate-400 uppercase mb-3">Estimativas</h3>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <div className="text-2xl font-bold text-green-400">${costData.estimates?.daily?.toFixed(2) || '0.00'}</div>
                    <div className="text-xs text-slate-400">Diário</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-yellow-400">${costData.estimates?.monthly?.toFixed(2) || '0.00'}</div>
                    <div className="text-xs text-slate-400">Mensal</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-blue-400">${costData.estimates?.yearly?.toFixed(2) || '0.00'}</div>
                    <div className="text-xs text-slate-400">Anual</div>
                  </div>
                </div>
              </div>

              {/* Session Usage */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-sm font-bold text-slate-400 uppercase mb-3">Sessão Atual</h3>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-slate-300">Requests:</span>
                  <span className="text-white font-bold">{costData.session?.total_requests || 0}</span>
                </div>
                <div className="flex justify-between items-center mb-3">
                  <span className="text-slate-300">Custo:</span>
                  <span className="text-green-400 font-bold">${costData.session?.total_cost?.toFixed(5) || '0.00000'}</span>
                </div>

                {/* Model Breakdown */}
                <div className="space-y-2">
                  {costData.session?.breakdown?.map((model, idx) => (
                    <div key={model.model || idx} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: model.color }}
                      ></div>
                      <span className="text-xs text-slate-300 flex-1">{model.display_name}</span>
                      <span className="text-xs text-slate-400">{model.requests} req</span>
                      <span className="text-xs text-green-400">${model.cost?.toFixed(5)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tier Info */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-sm font-bold text-slate-400 uppercase mb-2">Estratégia: {costData.routing_strategy?.toUpperCase()}</h3>
                <div className="text-xs text-slate-400 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    <span>Simples → Haiku ($0.001/1K)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
                    <span>Moderado → Gemini ($0.0005/1K)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                    <span>Complexo → Claude ($0.015/1K)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="bg-slate-800 p-3 rounded-b-lg border-t border-slate-700 flex justify-end">
              <button
                onClick={() => setShowCosts(false)}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm transition-colors font-semibold"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Routing Modal */}
      {showRouting && routingData && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg shadow-2xl border border-slate-700 w-full max-w-lg">
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-4 rounded-t-lg flex justify-between items-center">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <span>📈</span> AI Routing
              </h2>
              <button
                onClick={() => setShowRouting(false)}
                className="text-white hover:bg-white/20 rounded-lg px-3 py-1 text-xl transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-4">
              {/* Key Metrics */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-slate-800 rounded-lg p-3">
                  <div className="text-2xl font-bold text-purple-400">{routingData.total_requests || 0}</div>
                  <div className="text-xs text-slate-400">Total Requests</div>
                </div>
                <div className="bg-slate-800 rounded-lg p-3">
                  <div className="text-2xl font-bold text-green-400">${routingData.total_cost?.toFixed(4) || '0.00'}</div>
                  <div className="text-xs text-slate-400">Total Cost</div>
                </div>
                <div className="bg-slate-800 rounded-lg p-3">
                  <div className="text-2xl font-bold text-cyan-400">{((routingData.free_ratio || 0) * 100).toFixed(1)}%</div>
                  <div className="text-xs text-slate-400">Free (Ollama)</div>
                </div>
              </div>

              {/* Per-Model Breakdown */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-sm font-bold text-slate-400 uppercase mb-3">Per-Model Breakdown</h3>
                <div className="space-y-3">
                  {routingData.models && Object.entries(routingData.models).map(([name, data]) => {
                    const maxReqs = Math.max(...Object.values(routingData.models).map(m => m.requests || 0), 1);
                    const barWidth = ((data.requests || 0) / maxReqs) * 100;
                    const isOllama = name.includes('ollama');
                    const color = isOllama ? '#22c55e' : name === 'claude' ? '#ef4444' : name === 'gemini' ? '#eab308' : '#a855f7';
                    return (
                      <div key={name}>
                        <div className="flex justify-between items-center mb-1">
                          <div className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }}></div>
                            <span className="text-sm text-slate-300">{name}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-slate-400">{data.requests || 0} req</span>
                            <span className="text-xs text-slate-400">{Math.round(data.avg_latency_ms || 0)}ms</span>
                            <span className="text-xs font-bold" style={{ color }}>${(data.cost || 0).toFixed(4)}</span>
                          </div>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-1.5">
                          <div className="h-full rounded-full transition-all" style={{ width: `${barWidth}%`, backgroundColor: color }}></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Tier Distribution */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-sm font-bold text-slate-400 uppercase mb-3">Tier Distribution</h3>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <div className="text-lg font-bold text-green-400">{routingData.tier_distribution?.simple || 0}</div>
                    <div className="text-xs text-slate-400">Simple (Free)</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold text-yellow-400">{routingData.tier_distribution?.moderate || 0}</div>
                    <div className="text-xs text-slate-400">Moderate</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold text-red-400">{routingData.tier_distribution?.complex || 0}</div>
                    <div className="text-xs text-slate-400">Complex</div>
                  </div>
                </div>
              </div>

              {/* Strategy */}
              <div className="text-center text-xs text-slate-500">
                Strategy: <span className="text-slate-300 font-medium">{routingData.routing_strategy?.toUpperCase()}</span>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="bg-slate-800 p-3 rounded-b-lg border-t border-slate-700 flex justify-end">
              <button
                onClick={() => setShowRouting(false)}
                className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm transition-colors font-semibold"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      </div>{/* closes flex-1 flex overflow-hidden (2-column wrapper) */}
    </div>
  );
}
