import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useSidebarStore } from './useSidebarStore';
import MobileSidebar from './MobileSidebar';
import { useAuth } from '../contexts/AuthContext';

export default function Layout() {
  const { t, i18n } = useTranslation();
  const toggle = useSidebarStore(s => s.toggle);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  const roleLabel = user ? (t(`role.${user.role}`, user.role)) : '';

  const NAV = [
    { to: '/', label: t('nav.dashboard'), short: '🏠' },
    { to: '/equipment', label: t('nav.equipment'), short: t('nav.equipment').slice(0, 2) },
    { to: '/plant', label: t('nav.plant'), short: t('nav.plant').slice(0, 2) },
    { to: '/environment', label: t('nav.environment'), short: t('nav.environment').slice(0, 2) },
    { to: '/simulation', label: t('nav.simulation'), short: t('nav.simulation').slice(0, 2) },
    { to: '/strategies', label: t('nav.strategies'), short: t('nav.strategies').slice(0, 2) },
    { to: '/reports', label: t('nav.reports'), short: t('nav.reports').slice(0, 2) },
    { to: '/alerts', label: t('nav.alerts'), short: t('nav.alerts').slice(0, 2) },
    { to: '/override', label: t('nav.override'), short: t('nav.override').slice(0, 2) },
    { to: '/settings', label: t('nav.settings'), short: t('nav.settings').slice(0, 2) },
    { section: t('nav.monitoringSection') },
    { to: '/energy/dashboard', label: t('nav.energy'), short: t('nav.energy').slice(0, 2) },
    { to: '/health/dashboard', label: t('nav.health'), short: t('nav.health').slice(0, 2) },
    { section: t('nav.operationsSection') },
    { to: '/edges', label: t('nav.edges'), short: t('nav.edges').slice(0, 2) },
    { to: '/workorders', label: t('nav.workorders'), short: t('nav.workorders').slice(0, 2) },
    { to: '/maintenance', label: t('nav.maintenance'), short: t('nav.maintenance').slice(0, 2) },
    { to: '/carbon', label: t('nav.carbon'), short: t('nav.carbon').slice(0, 2) },
  ];

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100">
      {/* Desktop/Tablet Sidebar — hidden on mobile */}
      <aside className="hidden md:flex md:w-14 lg:w-56 flex-col bg-slate-800 border-r border-slate-700 p-4 transition-all">
        <h1 className="hidden lg:block text-lg font-bold text-cyan-400 mb-6">HVAC Platform</h1>
        <span className="lg:hidden text-lg font-bold text-cyan-400 mb-6 text-center">H</span>
        <nav className="flex-1 space-y-1">
          {NAV.map(n => {
            if ('section' in n) {
              return (
                <div key={n.section} className="px-1 py-2 text-xs text-slate-600 font-semibold tracking-wide uppercase mt-4 first:mt-0">
                  <span className="hidden lg:inline">{n.section}</span>
                  <span className="lg:hidden text-center block">─</span>
                </div>
              );
            }
            return (
              <NavLink key={n.to} to={n.to} end={n.to === '/'}
                className={({isActive}) =>
                  `block px-3 py-2 rounded text-sm text-center lg:text-left ${
                    isActive ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
                  }`}
              >
                <span className="hidden lg:inline">{n.label}</span>
                <span className="lg:hidden" title={n.label}>{n.short}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Language toggle */}
        <div className="border-t border-slate-700 pt-3 mt-3">
          <button
            onClick={() => i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh')}
            className="w-full px-2 py-1.5 text-xs border border-slate-600 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          >
            {i18n.language === 'zh' ? 'EN' : '中文'}
          </button>
        </div>

        {/* User info and logout */}
        {user && (
          <div className="border-t border-slate-700 pt-3 mt-3">
            <div className="hidden lg:block text-sm text-slate-300 truncate" title={user.id}>
              ID: {user.id}
            </div>
            <div className="hidden lg:block">
              <span className="inline-block text-xs px-2 py-0.5 rounded bg-cyan-400/10 text-cyan-400 border border-cyan-400/30 mt-1">
                {roleLabel}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="w-full mt-2 px-2 py-1.5 text-xs text-slate-400 hover:text-red-400 hover:bg-red-400/10 rounded transition-colors text-center lg:text-left"
            >
              <span className="hidden lg:inline">{t('common.logout')}</span>
              <span className="lg:hidden" title={t('common.logout')}>⏻</span>
            </button>
          </div>
        )}
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-slate-800 border-b border-slate-700 shrink-0">
          <button onClick={toggle} className="text-slate-300 hover:text-white text-2xl leading-none">
            ☰
          </button>
          <h1 className="text-lg font-bold text-cyan-400">HVAC Platform</h1>
          <div className="flex-1" />
          <button
            onClick={() => i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh')}
            className="px-2 py-1 text-xs border border-slate-600 rounded hover:bg-slate-700 text-slate-400"
          >
            {i18n.language === 'zh' ? 'EN' : '中文'}
          </button>
        </header>

        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>

      <MobileSidebar />
    </div>
  );
}
