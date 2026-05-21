import { create } from 'zustand';
import type { Position3D } from './store';

export interface RemoteUser {
  id: string;
  name: string;
  color: string;
  position: Position3D;
  selectedId: string | null;
  lastSeen: number;
}

const USER_COLORS = ['#f97316', '#eab308', '#22c55e', '#3b82f6', '#a855f7', '#ec4899', '#14b8a6', '#f43f5e'];

function getOrCreateLocalId(): string {
  const key = 'collab_user_id';
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = `user-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    sessionStorage.setItem(key, id);
  }
  return id;
}

function getLocalColor(userId: string): string {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = userId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return USER_COLORS[Math.abs(hash) % USER_COLORS.length];
}

interface CollaborationState {
  localUserId: string;
  localUserColor: string;
  remoteUsers: Record<string, RemoteUser>;
  updateRemoteUser: (user: RemoteUser) => void;
  removeRemoteUser: (id: string) => void;
}

export const useCollaborationStore = create<CollaborationState>((set) => {
  const localUserId = getOrCreateLocalId();
  return {
    localUserId,
    localUserColor: getLocalColor(localUserId),
    remoteUsers: {},
    updateRemoteUser: (user) =>
      set(s => ({
        remoteUsers: { ...s.remoteUsers, [user.id]: user },
      })),
    removeRemoteUser: (id) =>
      set(s => {
        const { [id]: _, ...rest } = s.remoteUsers;
        return { remoteUsers: rest };
      }),
  };
});
