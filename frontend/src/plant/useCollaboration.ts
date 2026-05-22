import { useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { usePlantStore } from './store';
import { useCollaborationStore } from './collaborationStore';

export function useCollaboration(plantId?: string) {
  const localUserId = useCollaborationStore(s => s.localUserId);
  const localUserColor = useCollaborationStore(s => s.localUserColor);
  const updateRemoteUser = useCollaborationStore(s => s.updateRemoteUser);
  const removeRemoteUser = useCollaborationStore(s => s.removeRemoteUser);
  const remoteCount = useCollaborationStore(s => Object.keys(s.remoteUsers).length);

  const remoteSourceRef = useRef(false);
  const prevLenRef = useRef({ eq: 0, pipe: 0 });
  const prevSelRef = useRef<string | null>(null);

  const { wsRef, status } = useWebSocket({
    endpoint: plantId ? `/ws/collaboration/${plantId}` : '/ws/collaboration',
    onMessage: (data) => {
      switch (data.type) {
        case 'plant_mutation': {
          if (data.user_id === localUserId) return;
          remoteSourceRef.current = true;
          const store = usePlantStore.getState();
          if (Array.isArray(data.equipment)) {
            store.loadPlantData({
              id: (data.plant_id as string) || store.plantId || '',
              name: store.plantName,
              equipment: data.equipment as Parameters<typeof store.loadPlantData>[0]['equipment'],
              pipe_segments: (data.pipe_segments || []) as Parameters<typeof store.loadPlantData>[0]['pipe_segments'],
            });
          }
          break;
        }
        case 'cursor_update': {
          if (data.user_id === localUserId) return;
          updateRemoteUser({
            id: data.user_id as string,
            name: (data.user_name as string) || (data.user_id as string),
            color: (data.color as string) || '#94a3b8',
            position: (data.position as { x: number; y: number; z: number }) || { x: 0, y: 0, z: 0 },
            selectedId: (data.selected_id as string) || null,
            lastSeen: Date.now(),
          });
          break;
        }
        case 'user_left':
          if (typeof data.user_id === 'string' && data.user_id !== localUserId) {
            removeRemoteUser(data.user_id);
          }
          break;
      }
    },
  });

  // Subscribe to store changes and broadcast local mutations
  useEffect(() => {
    const unsub = usePlantStore.subscribe((state, prevState) => {
      if (remoteSourceRef.current) {
        remoteSourceRef.current = false;
        prevLenRef.current = { eq: state.equipment.length, pipe: state.pipeSegments.length };
        prevSelRef.current = state.selectedId;
        return;
      }

      // Skip if no meaningful change (just selection toggle)
      const currEq = state.equipment.length;
      const currPipe = state.pipeSegments.length;
      const currSel = state.selectedId;

      if (currEq === prevLenRef.current.eq && currPipe === prevLenRef.current.pipe && currSel === prevSelRef.current) {
        return;
      }

      // Differentiate position changes (no count change) vs structural changes
      const structuralChange = currEq !== prevLenRef.current.eq || currPipe !== prevLenRef.current.pipe;

      prevLenRef.current = { eq: currEq, pipe: currPipe };
      prevSelRef.current = currSel;

      if (!structuralChange) return; // skip cursor-only updates for plant_mutation broadcast

      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'plant_mutation',
          plant_id: plantId || state.plantId,
          user_id: localUserId,
          equipment: state.equipment,
          pipe_segments: state.pipeSegments,
        }));
      }
    });

    return () => unsub();
  }, [plantId, localUserId, wsRef]);

  // Broadcast cursor position periodically
  useEffect(() => {
    const sendCursor = () => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      const state = usePlantStore.getState();
      const selected = state.equipment.find(e => e.id === state.selectedId);
      ws.send(JSON.stringify({
        type: 'cursor_update',
        user_id: localUserId,
        user_name: localUserId.slice(0, 8),
        color: localUserColor,
        position: selected?.position || { x: 0, y: 0, z: 0 },
        selected_id: state.selectedId,
      }));
    };

    const timer = setInterval(sendCursor, 2000);
    return () => clearInterval(timer);
  }, [localUserId, localUserColor, wsRef]);

  // Dev-mode simulation: fake remote user when disconnected
  useEffect(() => {
    if (status === 'connected') return;

    const fakeId = 'sim-user-01';
    const sim = setInterval(() => {
      const eqs = usePlantStore.getState().equipment;
      if (eqs.length === 0) return;
      const target = eqs[Math.floor(Math.random() * eqs.length)];
      updateRemoteUser({
        id: fakeId,
        name: '模拟用户',
        color: '#f97316',
        position: {
          x: target.position.x + (Math.random() - 0.5) * 2,
          y: target.position.y + 1,
          z: target.position.z + (Math.random() - 0.5) * 2,
        },
        selectedId: target.id,
        lastSeen: Date.now(),
      });
    }, 3000);

    return () => clearInterval(sim);
  }, [status, updateRemoteUser]);

  // Cleanup stale remote users (>15s no update)
  useEffect(() => {
    const cleanup = setInterval(() => {
      const users = useCollaborationStore.getState().remoteUsers;
      const now = Date.now();
      for (const [id, user] of Object.entries(users)) {
        if (now - user.lastSeen > 15000) {
          removeRemoteUser(id);
        }
      }
    }, 5000);
    return () => clearInterval(cleanup);
  }, [removeRemoteUser]);

  return { status, remoteCount, localUserId, localUserColor };
}
