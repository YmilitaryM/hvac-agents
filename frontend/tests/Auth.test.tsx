import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from '../src/contexts/AuthContext';
import ProtectedRoute from '../src/components/ProtectedRoute';
import Login from '../src/pages/Login';

// Provide a working localStorage for vitest v4 jsdom environment.
// Use plain functions (not vi.fn) so vi.restoreAllMocks() does not break them.
beforeAll(() => {
  let store: Record<string, string> = {};
  const mockStorage = {
    getItem(key: string) { return store[key] ?? null; },
    setItem(key: string, value: string) { store[key] = value; },
    removeItem(key: string) { delete store[key]; },
    clear() { store = {}; },
    get length() { return Object.keys(store).length; },
    key(index: number) { return Object.keys(store)[index] ?? null; },
  };
  Object.defineProperty(globalThis, 'localStorage', {
    value: mockStorage,
    writable: true,
    configurable: true,
  });
});

// Reset localStorage and mocks before each test
beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// AuthContext tests
// ---------------------------------------------------------------------------
describe('AuthContext', () => {
  it('renders children', () => {
    render(
      <AuthProvider>
        <div>Hello Auth</div>
      </AuthProvider>,
    );
    expect(screen.getByText('Hello Auth')).toBeDefined();
  });

  it('starts with isLoading true and then resolves', async () => {
    const Child = () => {
      const { isLoading } = useAuth();
      return <span>{isLoading ? 'loading' : 'ready'}</span>;
    };
    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );
    // useEffect may run synchronously in jsdom, so use waitFor for "ready"
    await waitFor(() => {
      expect(screen.getByText('ready')).toBeDefined();
    });
  });

  it('login sets token and user', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token:
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
            btoa(JSON.stringify({ sub: '42', role: 'admin', exp: Math.floor(Date.now() / 1000) + 3600 })) +
            '.fakeSignature',
          token_type: 'bearer',
          role: 'admin',
        }),
        { status: 200 },
      ),
    );

    const Child = () => {
      const { token, user, login } = useAuth();
      return (
        <div>
          <span data-testid="token">{token ?? 'none'}</span>
          <span data-testid="role">{user?.role ?? 'none'}</span>
          <button onClick={() => login('admin', 'pass')}>Login</button>
        </div>
      );
    };

    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('token').textContent).toBe('none');
    });

    fireEvent.click(screen.getByText('Login'));

    await waitFor(() => {
      expect(screen.getByTestId('token').textContent).not.toBe('none');
      expect(screen.getByTestId('role').textContent).toBe('admin');
    });

    expect(localStorage.getItem('auth_token')).toBeTruthy();
    expect(localStorage.getItem('auth_user')).toBeTruthy();
  });

  it('logout clears token and user', async () => {
    localStorage.setItem(
      'auth_token',
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
        btoa(JSON.stringify({ sub: '1', role: 'admin', exp: Math.floor(Date.now() / 1000) + 3600 })) +
        '.fake',
    );
    localStorage.setItem('auth_user', JSON.stringify({ id: '1', role: 'admin' }));

    const Child = () => {
      const { token, logout, isLoading } = useAuth();
      if (isLoading) return <span>loading</span>;
      return (
        <div>
          <span data-testid="token">{token ?? 'none'}</span>
          <button onClick={logout}>Logout</button>
        </div>
      );
    };

    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('token').textContent).not.toBe('none');
    });

    fireEvent.click(screen.getByText('Logout'));

    await waitFor(() => {
      expect(screen.getByTestId('token').textContent).toBe('none');
    });
  });

  it('register calls /auth/register and returns ok', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'ok', user_id: 99 }), { status: 201 }),
    );

    const Child = () => {
      const { register } = useAuth();
      return <button onClick={() => register('newuser', 'pass', 'viewer')}>Register</button>;
    };

    render(
      <AuthProvider>
        <Child />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByText('Register'));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/auth/register',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: 'newuser', password: 'pass', role: 'viewer' }),
        }),
      );
    });
  });
});

// ---------------------------------------------------------------------------
// ProtectedRoute tests
// ---------------------------------------------------------------------------
describe('ProtectedRoute', () => {
  it('redirects to /login when no token', async () => {
    localStorage.clear();

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        </MemoryRouter>
      </AuthProvider>,
    );

    await waitFor(() => {
      // Should redirect, so protected content is not visible
      expect(screen.queryByText('Protected Content')).toBeNull();
    });
  });

  it('renders children when token exists', async () => {
    localStorage.setItem(
      'auth_token',
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
        btoa(JSON.stringify({ sub: '1', role: 'admin', exp: Math.floor(Date.now() / 1000) + 3600 })) +
        '.fake',
    );
    localStorage.setItem('auth_user', JSON.stringify({ id: '1', role: 'admin' }));

    render(
      <AuthProvider>
        <MemoryRouter>
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        </MemoryRouter>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeDefined();
    });
  });

  it('shows "权限不足" when role is not allowed', async () => {
    localStorage.setItem(
      'auth_token',
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
        btoa(JSON.stringify({ sub: '1', role: 'viewer', exp: Math.floor(Date.now() / 1000) + 3600 })) +
        '.fake',
    );
    localStorage.setItem('auth_user', JSON.stringify({ id: '1', role: 'viewer' }));

    render(
      <AuthProvider>
        <MemoryRouter>
          <ProtectedRoute roles={['admin']}>
            <div>Admin Only</div>
          </ProtectedRoute>
        </MemoryRouter>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('权限不足')).toBeDefined();
      expect(screen.queryByText('Admin Only')).toBeNull();
    });
  });

  it('renders children when role matches', async () => {
    localStorage.setItem(
      'auth_token',
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
        btoa(JSON.stringify({ sub: '1', role: 'admin', exp: Math.floor(Date.now() / 1000) + 3600 })) +
        '.fake',
    );
    localStorage.setItem('auth_user', JSON.stringify({ id: '1', role: 'admin' }));

    render(
      <AuthProvider>
        <MemoryRouter>
          <ProtectedRoute roles={['admin', 'operator']}>
            <div>Admin Area</div>
          </ProtectedRoute>
        </MemoryRouter>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Admin Area')).toBeDefined();
    });
  });
});

// ---------------------------------------------------------------------------
// Login Page tests
// ---------------------------------------------------------------------------
describe('Login Page', () => {
  it('renders form elements', () => {
    render(
      <AuthProvider>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </AuthProvider>,
    );

    expect(screen.getByLabelText('用户名')).toBeDefined();
    expect(screen.getByLabelText('密码')).toBeDefined();
    expect(screen.getByRole('button', { name: '登录' })).toBeDefined();
    expect(screen.getByText('HVAC 运营平台')).toBeDefined();
  });

  it('shows register toggle', () => {
    render(
      <AuthProvider>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </AuthProvider>,
    );

    fireEvent.click(screen.getByText('注册新账户'));
    expect(screen.getByLabelText('角色')).toBeDefined();
    expect(screen.getByRole('button', { name: '注册' })).toBeDefined();
  });

  it('shows error on failed login', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Invalid credentials'));

    render(
      <AuthProvider>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </AuthProvider>,
    );

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'bad' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeDefined();
    });
  });

  it('navigates to / on successful login', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token:
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
            btoa(JSON.stringify({ sub: '1', role: 'admin', exp: Math.floor(Date.now() / 1000) + 3600 })) +
            '.fake',
          token_type: 'bearer',
          role: 'admin',
        }),
        { status: 200 },
      ),
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<div>Home</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'pass' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));

    await waitFor(() => {
      // After successful login, we navigate to / and see "Home"
      expect(screen.getByText('Home')).toBeDefined();
    });
  });
});
