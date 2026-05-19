import { Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <div className="flex h-screen bg-slate-900 text-slate-100">
      <aside className="w-56 bg-slate-800 border-r border-slate-700 p-4">
        <h1 className="text-lg font-bold text-cyan-400 mb-6">HVAC Platform</h1>
        <nav className="space-y-1">
          <span className="block px-3 py-2 rounded text-sm text-slate-400">Loading nav...</span>
        </nav>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
