import { useEffect, useRef, useState } from 'react';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

interface UseWebSocketOptions {
  onMessage: (data: Record<string, unknown>) => void;
  endpoint?: string;
}

export function useWebSocket({ onMessage, endpoint = '/ws/monitor' }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${location.host}${endpoint}`);
      wsRef.current = ws;
      setStatus('connecting');

      ws.onopen = () => {
        if (cancelled) { ws.close(); return; }
        retryCountRef.current = 0;
        setStatus('connected');
        ws.send(JSON.stringify({ subscribe: ['strategy_created', 'anomaly_detected', 'sensor_reading'] }));
      };

      ws.onmessage = (evt) => {
        try { onMessage(JSON.parse(evt.data)); } catch { /* ignore malformed messages */ }
      };

      ws.onclose = () => {
        if (cancelled) return;
        setStatus('disconnected');
        const delay = Math.min(1000 * 2 ** retryCountRef.current, 30000);
        retryCountRef.current += 1;
        timerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [endpoint]);

  return { wsRef, status };
}
