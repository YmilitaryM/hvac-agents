import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const { t } = useTranslation();
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
        await login(username, password);
      } else {
        await login(username, password);
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : t('login.operationFailed'));
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 max-w-sm w-full">
        <h1 className="text-2xl font-bold text-slate-100 text-center mb-1">
          {t('login.title')}
        </h1>
        <p className="text-slate-400 text-center mb-6">
          {isRegisterMode ? t('login.createAccount') : t('login.loginAccount')}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm text-slate-300 mb-1">
              {t('login.username')}
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400"
              placeholder={t('login.placeholderUsername')}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm text-slate-300 mb-1">
              {t('login.password')}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400"
              placeholder={t('login.placeholderPassword')}
            />
          </div>

          {isRegisterMode && (
            <div>
              <label htmlFor="role" className="block text-sm text-slate-300 mb-1">
                {t('login.role')}
              </label>
              <select
                id="role"
                value={role}
                onChange={e => setRole(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded text-slate-100 focus:outline-none focus:border-cyan-400"
              >
                <option value="viewer">{t('role.viewer')}</option>
                <option value="operator">{t('role.operator')}</option>
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
            {isPending ? (isRegisterMode ? t('common.registering') : t('common.loggingIn')) : (isRegisterMode ? t('login.register') : t('login.login'))}
          </button>
        </form>

        <p className="text-slate-400 text-sm text-center mt-6">
          {isRegisterMode ? (
            <>
              {t('login.hasAccount')}{' '}
              <button
                type="button"
                onClick={() => { setIsRegisterMode(false); setError(''); }}
                className="text-cyan-400 hover:text-cyan-300"
              >
                {t('login.backToLogin')}
              </button>
            </>
          ) : (
            <>
              {t('login.noAccount')}{' '}
              <button
                type="button"
                onClick={() => { setIsRegisterMode(true); setError(''); }}
                className="text-cyan-400 hover:text-cyan-300"
              >
                {t('login.registerAccount')}
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
