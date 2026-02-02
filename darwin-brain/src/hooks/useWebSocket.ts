import { useEffect, useRef, useCallback } from 'react';
import { useDarwinStore } from '../store/darwinStore';
import { WS_URL } from '../utils/api';
import type { WebSocketMessage, Activity, Dream, Discovery } from '../types/darwin';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);

  const setConnected = useDarwinStore((state) => state.setConnected);
  const setStatus = useDarwinStore((state) => state.setStatus);
  const addActivity = useDarwinStore((state) => state.addActivity);
  const addDream = useDarwinStore((state) => state.addDream);
  const addDiscovery = useDarwinStore((state) => state.addDiscovery);
  const addThought = useDarwinStore((state) => state.addThought);
  const setCurrentDream = useDarwinStore((state) => state.setCurrentDream);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WebSocketMessage = JSON.parse(event.data);

      switch (data.type) {
        case 'status_update':
          setStatus(data.payload as Record<string, unknown>);
          break;

        case 'activity_start':
        case 'activity_complete': {
          const activity = data.payload as Activity;
          addActivity({
            ...activity,
            timestamp: new Date(activity.timestamp),
          });

          // Add as thought node
          addThought({
            id: activity.id,
            type: 'thought',
            content: activity.title,
            title: activity.title,
            timestamp: new Date(activity.timestamp),
            position: [
              (Math.random() - 0.5) * 8,
              (Math.random() - 0.5) * 8,
              (Math.random() - 0.5) * 8,
            ],
            connections: [],
            intensity: 0.8,
          });
          break;
        }

        case 'dream': {
          const dream = data.payload as Dream;
          addDream({
            ...dream,
            timestamp: new Date(dream.timestamp),
          });
          setCurrentDream({
            ...dream,
            timestamp: new Date(dream.timestamp),
          });

          // Add dream as thought
          addThought({
            id: dream.id,
            type: 'dream',
            content: dream.narrative,
            timestamp: new Date(dream.timestamp),
            position: [
              (Math.random() - 0.5) * 6,
              Math.random() * 4 + 2,
              (Math.random() - 0.5) * 6,
            ],
            connections: [],
            intensity: 1,
          });
          break;
        }

        case 'discovery': {
          const discovery = data.payload as Discovery;
          addDiscovery({
            ...discovery,
            timestamp: new Date(discovery.timestamp),
          });

          addThought({
            id: discovery.id,
            type: 'discovery',
            content: discovery.content,
            title: discovery.title,
            timestamp: new Date(discovery.timestamp),
            position: [
              (Math.random() - 0.5) * 8,
              (Math.random() - 0.5) * 8,
              (Math.random() - 0.5) * 8,
            ],
            connections: [],
            intensity: discovery.severity === 'critical' ? 1 : 0.7,
          });
          break;
        }

        case 'mood_change':
          setStatus({
            mood: (data.payload as { mood: string }).mood as any,
          });
          break;

        case 'state_change':
          setStatus({
            state: (data.payload as { state: string }).state as any,
          });
          break;

        case 'shower_thought': {
          const thought = data.payload as { thought: string };
          addThought({
            id: `thought-${Date.now()}`,
            type: 'thought',
            content: thought.thought,
            timestamp: new Date(),
            position: [0, 3, 0],
            connections: [],
            intensity: 0.9,
          });
          break;
        }

        case 'finding': {
          // Handle new finding notification
          const finding = data.payload as any;
          addThought({
            id: finding.id,
            type: 'finding',
            content: finding.description,
            title: finding.title,
            timestamp: new Date(finding.created_at || finding.timestamp),
            position: [
              (Math.random() - 0.5) * 10,
              (Math.random() - 0.5) * 10,
              (Math.random() - 0.5) * 10,
            ],
            connections: [],
            intensity: finding.priority === 'urgent' ? 1 : 0.6,
          });
          break;
        }

        case 'language_content': {
          // Handle new language evolution content
          // This is informational - the Language Evolution panel will refresh to show it
          const langContent = data.payload as any;
          console.log('New language content recorded:', langContent.type, langContent.id);
          break;
        }

        default:
          console.log('Unknown WebSocket message type:', data.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }, [setStatus, addActivity, addDream, addDiscovery, addThought, setCurrentDream]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      wsRef.current = new WebSocket(WS_URL);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        reconnectAttempts.current = 0;
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);

        // Reconnect with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current++;

        reconnectTimeoutRef.current = setTimeout(() => {
          console.log(`Attempting to reconnect (attempt ${reconnectAttempts.current})...`);
          connect();
        }, delay);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current.onmessage = handleMessage;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [handleMessage, setConnected]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnected(false);
  }, [setConnected]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return { connect, disconnect, send };
}

export default useWebSocket;
