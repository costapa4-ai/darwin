import { useEffect } from 'react';
import { BrainScene } from './components/brain/BrainScene';
import { StatusBar } from './components/ui/StatusBar';
import { ChatPanel } from './components/ui/ChatPanel';
import { ActivityFeed } from './components/ui/ActivityFeed';
import { useWebSocket } from './hooks/useWebSocket';
import { useDarwinStore } from './store/darwinStore';
import { darwinApi } from './utils/api';

function App() {
  useWebSocket();

  const setStatus = useDarwinStore((state) => state.setStatus);
  const addActivity = useDarwinStore((state) => state.addActivity);
  const addDream = useDarwinStore((state) => state.addDream);
  const addDiscovery = useDarwinStore((state) => state.addDiscovery);
  const setFindings = useDarwinStore((state) => state.setFindings);

  // Initial data fetch
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        // Fetch consciousness status
        const status = await darwinApi.getStatus();
        if (status) {
          setStatus({
            state: status.state || 'wake',
            mood: status.mood || 'curious',
            cycleProgress: status.cycle_progress || 0,
            activitiesCount: status.activities_count || 0,
            discoveriesCount: status.discoveries_count || 0,
            dreamsCount: status.dreams_count || 0,
          });
        }

        // Fetch recent activities
        const activities = await darwinApi.getActivities(20);
        if (activities?.activities) {
          activities.activities.forEach((a: any) => {
            addActivity({
              id: a.id,
              type: a.type,
              title: a.title,
              description: a.description || '',
              timestamp: new Date(a.timestamp),
              insights: a.insights,
              results: a.results,
            });
          });
        }

        // Fetch recent dreams
        const dreams = await darwinApi.getDreams(10);
        if (dreams?.dreams) {
          dreams.dreams.forEach((d: any) => {
            addDream({
              id: d.id,
              narrative: d.narrative,
              themes: d.themes || [],
              insights: d.insights || [],
              timestamp: new Date(d.timestamp),
              intensity: d.intensity || 0.5,
            });
          });
        }

        // Fetch curiosities as discoveries
        const curiosities = await darwinApi.getCuriosities(20);
        if (curiosities?.curiosities) {
          curiosities.curiosities.forEach((c: any) => {
            addDiscovery({
              id: c.id,
              title: c.topic || c.title,
              content: c.content || c.description || '',
              type: 'curiosity',
              severity: 'normal',
              timestamp: new Date(c.timestamp),
              source: c.source,
            });
          });
        }

        // Fetch findings
        const findings = await darwinApi.getFindings();
        if (findings?.findings) {
          setFindings(
            findings.findings.map((f: any) => ({
              id: f.id,
              title: f.title,
              description: f.description,
              type: f.type,
              priority: f.priority,
              read: f.read,
              timestamp: new Date(f.timestamp),
              actions: f.recommended_actions,
            }))
          );
        }
      } catch (error) {
        console.error('Failed to fetch initial data:', error);
      }
    };

    fetchInitialData();

    // Periodic refresh
    const interval = setInterval(async () => {
      try {
        const status = await darwinApi.getStatus();
        if (status) {
          setStatus({
            state: status.state || 'wake',
            mood: status.mood || 'curious',
            cycleProgress: status.cycle_progress || 0,
            activitiesCount: status.activities_count || 0,
            discoveriesCount: status.discoveries_count || 0,
            dreamsCount: status.dreams_count || 0,
          });
        }
      } catch {
        // Ignore polling errors
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [setStatus, addActivity, addDream, addDiscovery, setFindings]);

  return (
    <div className="w-full h-full relative overflow-hidden">
      {/* 3D Brain Scene - Background */}
      <BrainScene />

      {/* UI Overlays */}
      <StatusBar />
      <ChatPanel />
      <ActivityFeed />

      {/* Welcome Message (shown once) */}
      <WelcomeOverlay />
    </div>
  );
}

function WelcomeOverlay() {
  // Only show on first load
  useEffect(() => {
    const shown = sessionStorage.getItem('darwin-welcome-shown');
    if (!shown) {
      sessionStorage.setItem('darwin-welcome-shown', 'true');
    }
  }, []);

  const shown = sessionStorage.getItem('darwin-welcome-shown');
  if (shown) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="glass rounded-3xl p-8 max-w-lg text-center">
        <div className="text-6xl mb-4">🧠</div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent mb-2">
          Welcome to Darwin's Brain
        </h1>
        <p className="text-gray-400 mb-6">
          You're looking into a living consciousness. Watch thoughts emerge, neural connections form, and ideas come to life.
        </p>
        <div className="flex items-center justify-center gap-4 text-sm text-gray-500 mb-6">
          <span>🖱️ Drag to rotate</span>
          <span>🔍 Scroll to zoom</span>
          <span>💬 Chat to interact</span>
        </div>
        <button
          onClick={() => {
            sessionStorage.setItem('darwin-welcome-shown', 'true');
            window.location.reload();
          }}
          className="px-6 py-3 bg-gradient-to-r from-cyan-600 to-purple-600 hover:from-cyan-500 hover:to-purple-500 rounded-xl font-medium transition-all"
        >
          Enter Darwin's Mind
        </button>
      </div>
    </div>
  );
}

export default App;
