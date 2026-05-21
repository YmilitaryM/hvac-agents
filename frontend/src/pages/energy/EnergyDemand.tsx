import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function EnergyDemand() {
  const { data, isLoading } = useQuery({
    queryKey: ['energy-demand', 1],
    queryFn: () => energyApi.getDemand(1),
    refetchInterval: 30000,
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  const chartData = data.trend.map((v, i) => ({ idx: i, kw: v }));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">需量管理</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">当前需量</div>
          <div className="text-3xl font-bold">{data.current_kw} <span className="text-base text-gray-500">kW</span></div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">预测峰值</div>
          <div className={`text-3xl font-bold ${data.warning ? 'text-red-600' : 'text-green-600'}`}>
            {data.predicted_peak_kw} <span className="text-base text-gray-500">kW</span>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">需量限额</div>
          <div className="text-3xl font-bold text-blue-600">{data.demand_limit_kw} <span className="text-base text-gray-500">kW</span></div>
        </div>
      </div>
      {data.warning && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">需量预警：预测需量将超出限额</div>
      )}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">需量趋势</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="idx" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="kw" stroke="#ea580c" name="需量kW" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
