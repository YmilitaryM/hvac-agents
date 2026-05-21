import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function EnergyDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['energy-dashboard', 1],
    queryFn: () => energyApi.getDashboard(1),
    refetchInterval: 15000,
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  const chartData = data.trend.cop.map((v, i) => ({
    idx: i, cop: v, power: data.trend.power_kw[i], load: data.trend.load_rt[i]
  }));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">能效看板</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">系统 COP</div>
          <div className="text-3xl font-bold text-blue-600">{data.current_cop.toFixed(2)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">总功率 (kW)</div>
          <div className="text-3xl font-bold text-orange-600">{data.total_power_kw}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">冷负荷 (RT)</div>
          <div className="text-3xl font-bold text-cyan-600">{data.cooling_load_rt}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">电费 (元/时)</div>
          <div className="text-3xl font-bold text-red-600">{data.electricity_cost_per_hour}</div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">24h 能效趋势</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="idx" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Line yAxisId="left" type="monotone" dataKey="cop" stroke="#2563eb" name="COP" />
            <Line yAxisId="right" type="monotone" dataKey="power" stroke="#ea580c" name="功率kW" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">分项能耗占比</h2>
        <div className="flex justify-around text-center">
          <div><div className="text-2xl font-bold text-blue-600">{data.equipment_breakdown.chillers} kW</div><div className="text-sm text-gray-500">冷水机组</div></div>
          <div><div className="text-2xl font-bold text-green-600">{data.equipment_breakdown.pumps} kW</div><div className="text-sm text-gray-500">水泵</div></div>
          <div><div className="text-2xl font-bold text-purple-600">{data.equipment_breakdown.cooling_towers} kW</div><div className="text-sm text-gray-500">冷却塔</div></div>
        </div>
      </div>
    </div>
  );
}
