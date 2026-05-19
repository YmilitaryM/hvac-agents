import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import KpiCard from '../components/KpiCard';

export default function Dashboard() {
  const { data: kpi } = useQuery({
    queryKey: ['kpi'],
    queryFn: () => fetch('/api/monitoring/kpi').then(r => r.json()),
    refetchInterval: 5000,
  });

  const k = kpi?.kpi || {};

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">系统总览</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="系统 COP" value={k.system_cop?.toFixed(2) || '--'} color="text-cyan-400" />
        <KpiCard label="冷负荷 (RT)" value={k.total_cooling_load_rt?.toFixed(0) || '--'} />
        <KpiCard label="总功率 (kW)" value={k.total_power_kw?.toFixed(0) || '--'} />
        <KpiCard label="室外湿球温度 (°C)" value={k.outdoor_wb_temp?.toFixed(1) || '--'} />
      </div>

      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <h3 className="text-sm text-slate-400 uppercase mb-3">COP 趋势</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={[]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip />
            <Line type="monotone" dataKey="cop" stroke="#38bdf8" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
