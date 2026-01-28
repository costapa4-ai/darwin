/**
 * Dynamic URL resolution based on browser hostname.
 * Supports multiple access methods: localhost, 192.168.1.117, myserver.local
 */

const URL_MAP = {
  'localhost': { api: 'http://localhost:8000', ws: 'ws://localhost:8000' },
  '127.0.0.1': { api: 'http://localhost:8000', ws: 'ws://localhost:8000' },
  '192.168.1.117': { api: 'http://192.168.1.117:8000', ws: 'ws://192.168.1.117:8000' },
  'myserver.local': { api: 'http://myserver.local:8000', ws: 'ws://myserver.local:8000' },
};

function getUrls() {
  const hostname = window.location.hostname;

  if (URL_MAP[hostname]) {
    return URL_MAP[hostname];
  }

  // Fallback: use same hostname as frontend with port 8000
  const protocol = window.location.protocol;
  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
  return {
    api: `${protocol}//${hostname}:8000`,
    ws: `${wsProtocol}//${hostname}:8000`
  };
}

// Check environment variables first
export const API_BASE = import.meta.env.VITE_API_URL || getUrls().api;
export const WS_BASE = import.meta.env.VITE_WS_URL || getUrls().ws;

// Log for debugging
console.log(`[Darwin Config] API: ${API_BASE}, WS: ${WS_BASE}`);
