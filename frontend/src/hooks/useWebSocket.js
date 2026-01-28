import { useEffect, useState, useCallback, useRef } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
const RECONNECT_DELAY = 3000; // 3 seconds

export function useWebSocket() {
  const [socket, setSocket] = useState(null);
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef(null);
  const shouldConnectRef = useRef(true);

  const connect = useCallback(() => {
    if (!shouldConnectRef.current) return;

    console.log('🔌 Attempting to connect to WebSocket...');
    const ws = new WebSocket(`${WS_URL}/ws`);

    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
      // Clear any pending reconnect attempts
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        let messageData = JSON.parse(event.data);

        // Handle double-encoded JSON (backend sends JSON string of JSON)
        if (typeof messageData === 'string') {
          messageData = JSON.parse(messageData);
        }

        // Create a proper object with an id
        const newEvent = {
          id: Date.now(),
          type: messageData.type,
          message_type: messageData.message_type,
          priority: messageData.priority,
          message: messageData.message,
          data: messageData.data,
          mood: messageData.mood,
          mood_intensity: messageData.mood_intensity,
          timestamp: messageData.timestamp
        };

        setEvents((prev) => [...prev, newEvent]);
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      setIsConnected(false);
      setSocket(null);

      // Attempt to reconnect after delay
      if (shouldConnectRef.current) {
        console.log(`🔄 Reconnecting in ${RECONNECT_DELAY / 1000}s...`);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, RECONNECT_DELAY);
      }
    };

    setSocket(ws);
  }, []);

  useEffect(() => {
    shouldConnectRef.current = true;
    connect();

    return () => {
      // Clean up on unmount
      shouldConnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [connect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    socket,
    events,
    isConnected,
    clearEvents
  };
}
