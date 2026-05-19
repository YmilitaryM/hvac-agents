import { useEffect, useRef } from 'react';

export function useWebSocket(onMessage: (data: Record<string, unknown>) => void) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${location.host}/ws/monitor`);
    wsRef.current = ws;

    ws.onopen = () => ws.send(JSON.stringify({ subscribe: ['strategy_created', 'anomaly_detected'] }));
    ws.onmessage = (evt) => {
      try { onMessage(JSON.parse(evt.data)); } catch { /* ignore malformed messages */ }
    };
    ws.onclose = () => setTimeout(() => { /* reconnect: effect will re-run if component remounts */ }, 3000);

    return () => ws.close();
  }, []);

  return wsRef;
}
