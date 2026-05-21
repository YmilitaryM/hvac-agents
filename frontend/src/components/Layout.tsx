import { Outlet, NavLink } from 'react-router-dom';
import { useSidebarStore } from './useSidebarStore';
import MobileSidebar from './MobileSidebar';

const NAV = [
  { to: '/', label: 'Dashboard', short: '🏠' },
  { to: '/equipment', label: '设备管理', short: '设备' },
  { to: '/plant', label: '制冷站', short: '制冷' },
  { to: '/environment', label: '环境配置', short: '环境' },
  { to: '/simulation', label: '仿真控制', short: '仿真' },
  { to: '/strategies', label: '策略中心', short: '策略' },
  { to: '/reports', label: '报告', short: '报告' },
  { to: '/alerts', label: '告警', short: '告警' },
  { to: '/override', label: '手动干预', short: '干预' },
  { to: '/settings', label: '系统设置', short: '设置' },
  { section: '── 边缘运营 ──' },
  { to: '/edges', label: '边缘设备', short: '边缘' },
  { to: '/workorders', label: '工单管理', short: '工单' },
  { to: '/maintenance', label: '预测维护', short: '维护' },
  { to: '/carbon', label: '碳管理', short: '碳' },
];

export default function Layout() {
  const toggle = useSidebarStore(s => s.toggle);

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
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-slate-800 border-b border-slate-700 shrink-0">
          <button onClick={toggle} className="text-slate-300 hover:text-white text-2xl leading-none">
            ☰
          </button>
          <h1 className="text-lg font-bold text-cyan-400">HVAC Platform</h1>
        </header>

        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>

      <MobileSidebar />
    </div>
  );
}
