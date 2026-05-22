import { NavLink } from 'react-router-dom';
import { useSidebarStore } from './useSidebarStore';

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
  { section: '── 边缘运营 ──' },
  { to: '/edges', label: '边缘设备' },
  { to: '/workorders', label: '工单管理' },
  { to: '/maintenance', label: '预测维护' },
  { to: '/carbon', label: '碳管理' },
];

export default function MobileSidebar() {
  const isOpen = useSidebarStore(s => s.isOpen);
  const close = useSidebarStore(s => s.close);

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={close}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-64 bg-slate-800 border-r border-slate-700 p-4 overflow-y-auto
          transform transition-transform duration-200 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          md:hidden`}
      >
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-lg font-bold text-cyan-400">HVAC Platform</h1>
          <button onClick={close} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
        </div>

        <nav className="space-y-1">
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
                onClick={close}
                className={({isActive}) => `block px-3 py-2 rounded text-sm ${isActive ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
                {n.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
