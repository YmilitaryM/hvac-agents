import { Outlet, NavLink } from 'react-router-dom';

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/equipment', label: '设备管理' },
  { to: '/plant', label: '制冷站' },
  { to: '/environment', label: '环境配置' },
  { to: '/simulation', label: '仿真控制' },
  { to: '/strategies', label: '策略中心' },
  { to: '/reports', label: '报告' },
  { to: '/alerts', label: '告警' },
  { to: '/override', label: '手动干预' },
  { to: '/settings', label: '系统设置' },
  // P3-D Edge Ops section
  { section: '── Edge Ops ──' },
  { to: '/edges', label: '🖥️ Edge Devices' },
  { to: '/workorders', label: '🔧 Work Orders' },
  { to: '/maintenance', label: '🔮 Maintenance' },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-slate-900 text-slate-100">
      <aside className="w-56 bg-slate-800 border-r border-slate-700 p-4 flex flex-col">
        <h1 className="text-lg font-bold text-cyan-400 mb-6">HVAC Platform</h1>
        <nav className="flex-1 space-y-1">
          {NAV.map(n => {
            if ('section' in n) {
              return (
                <div key={n.section} className="px-3 py-2 text-xs text-slate-500 font-semibold tracking-wide uppercase mt-4 first:mt-0">
                  {n.section}
                </div>
              );
            }
            return (
              <NavLink key={n.to} to={n.to} end={n.to === '/'}
                className={({isActive}) => `block px-3 py-2 rounded text-sm ${isActive ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
                {n.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
