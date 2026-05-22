import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { setAuthToken } from '../api/client';

interface AuthUser {
  id: string;
  role: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (username: string, password: string, role?: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function decodeJwtPayload(token: string): { sub?: string; role?: string; exp?: number } | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
  });

  // On mount, restore session from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');

    if (storedToken && storedUser) {
      try {
        const payload = decodeJwtPayload(storedToken);
        if (payload && payload.exp && payload.exp * 1000 > Date.now()) {
          const user: AuthUser = JSON.parse(storedUser);
          setAuthToken(storedToken);
          setState({ user, token: storedToken, isLoading: false });
          return;
        }
      } catch {
        // fall through to clear
      }
    }

    // No valid session
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setAuthToken(null);
    setState({ user: null, token: null, isLoading: false });
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(body || `登录失败 (HTTP ${response.status})`);
    }

    const data: { access_token: string; role: string } = await response.json();
    const token = data.access_token;
    const payload = decodeJwtPayload(token);
    const user: AuthUser = {
      id: payload?.sub ?? '0',
      role: data.role,
    };

    localStorage.setItem('auth_token', token);
    localStorage.setItem('auth_user', JSON.stringify(user));
    setAuthToken(token);
    setState({ user, token, isLoading: false });
  }, []);

  const register = useCallback(async (username: string, password: string, role?: string) => {
    const body: Record<string, string> = { username, password };
    if (role) body.role = role;

    const response = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errBody = await response.text().catch(() => '');
      throw new Error(errBody || `注册失败 (HTTP ${response.status})`);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setAuthToken(null);
    setState({ user: null, token: null, isLoading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
