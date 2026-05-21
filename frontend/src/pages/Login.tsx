import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string })?.from || '/';

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('viewer');
  const [error, setError] = useState('');
  const [isPending, setIsPending] = useState(false);
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setIsPending(true);

    try {
      if (isRegisterMode) {
        await register(username, password, role);
        // After successful registration, log in automatically
        await login(username, password);
      } else {
        await login(username, password);
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败，请重试');
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 max-w-sm w-full">
        <h1 className="text-2xl font-bold text-slate-100 text-center mb-1">
          HVAC 运营平台
        </h1>
        <p className="text-slate-400 text-center mb-6">
          {isRegisterMode ? '创建新账户' : '登录您的账户'}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm text-slate-300 mb-1">
              用户名
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400"
              placeholder="请输入用户名"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm text-slate-300 mb-1">
              密码
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400"
              placeholder="请输入密码"
            />
          </div>

          {isRegisterMode && (
            <div>
              <label htmlFor="role" className="block text-sm text-slate-300 mb-1">
                角色
              </label>
              <select
                id="role"
                value={role}
                onChange={e => setRole(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded text-slate-100 focus:outline-none focus:border-cyan-400"
              >
                <option value="viewer">查看者</option>
                <option value="operator">操作员</option>
              </select>
            </div>
          )}

          {error && (
            <div className="text-red-400 text-sm bg-red-400/10 border border-red-400/30 rounded px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded transition-colors"
          >
            {isPending ? (isRegisterMode ? '注册中...' : '登录中...') : (isRegisterMode ? '注册' : '登录')}
          </button>
        </form>

        <p className="text-slate-400 text-sm text-center mt-6">
          {isRegisterMode ? (
            <>
              已有账户？{' '}
              <button
                type="button"
                onClick={() => { setIsRegisterMode(false); setError(''); }}
                className="text-cyan-400 hover:text-cyan-300"
              >
                返回登录
              </button>
            </>
          ) : (
            <>
              还没有账户？{' '}
              <button
                type="button"
                onClick={() => { setIsRegisterMode(true); setError(''); }}
                className="text-cyan-400 hover:text-cyan-300"
              >
                注册新账户
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
