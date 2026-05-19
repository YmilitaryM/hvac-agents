import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchDailyReport } from '../api/reports';
import { fetchBenchmarking } from '../api/reports';
import KpiCard from '../components/KpiCard';

export default function Reports() {
  const [plantId, setPlantId] = useState('plant-1');

  const { data: report } = useQuery({
    queryKey: ['daily-report', plantId],
    queryFn: () => fetchDailyReport(plantId),
  });

  const { data: bench } = useQuery({
    queryKey: ['benchmarking'],
    queryFn: fetchBenchmarking,
  });

  const r = report || {};
  const kpi = r.kpi || {};
  const recommendations = r.recommendations || [];
  const plants = bench?.plants || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">报告</h2>
        <input
          value={plantId}
          onChange={e => setPlantId(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-32 text-sm"
          placeholder="Plant ID"
        />
      </div>

      {/* KPI Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <KpiCard label="日均 COP" value={kpi.avg_cop?.toFixed(2) || '--'} color="text-cyan-400" />
        <KpiCard label="总能耗 (kWh)" value={kpi.total_energy_kwh?.toFixed(0) || '--'} />
        <KpiCard label="碳排放 (kgCO₂)" value={kpi.carbon_kg?.toFixed(0) || '--'} />
        <KpiCard label="电费 (元)" value={kpi.electricity_cost?.toFixed(0) || '--'} />
      </div>

      {/* Strategy Stats Chart */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
        <h3 className="text-sm text-slate-400 uppercase mb-3">策略使用统计</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={[
            { name: '默认策略', count: 45 },
            { name: '节能优先', count: 32 },
            { name: '舒适优先', count: 18 },
            { name: 'DRL优化', count: 5 },
          ]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
            <Bar dataKey="count" fill="#38bdf8" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Recommendations + Benchmarking */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">优化建议</h3>
          {recommendations.length === 0 ? (
            <div className="text-slate-500 text-sm">
              <p>暂无建议。运行更多仿真以获取优化建议。</p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-slate-400">
                <li>提高冷冻水设定温度可降低能耗</li>
                <li>检查冷却塔风扇频率设定</li>
                <li>考虑夜间蓄冷策略降低峰时电费</li>
              </ul>
            </div>
          ) : (
            <ul className="space-y-2">
              {recommendations.map((rec: any, i: number) => (
                <li key={i} className="text-sm bg-slate-700 rounded p-2">{rec.text || rec}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">多站能效对标</h3>
          {plants.length === 0 ? (
            <div className="text-slate-500 text-sm">
              <table className="w-full text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="text-left py-1">排名</th>
                    <th className="text-left py-1">制冷站</th>
                    <th className="text-left py-1">COP</th>
                    <th className="text-left py-1">能耗强度</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { rank: 1, name: 'Plant A (北京)', cop: 5.2, intensity: '0.68 kW/RT' },
                    { rank: 2, name: 'Plant B (上海)', cop: 4.8, intensity: '0.73 kW/RT' },
                    { rank: 3, name: 'Plant C (广州)', cop: 4.3, intensity: '0.82 kW/RT' },
                  ].map(p => (
                    <tr key={p.rank} className="border-t border-slate-700">
                      <td className="py-1.5">{p.rank}</td>
                      <td className="py-1.5">{p.name}</td>
                      <td className="py-1.5 text-cyan-400">{p.cop}</td>
                      <td className="py-1.5">{p.intensity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-slate-400">
                <tr>
                  <th className="text-left py-1">排名</th>
                  <th className="text-left py-1">制冷站</th>
                  <th className="text-left py-1">COP</th>
                  <th className="text-left py-1">碳强 (kgCO₂/RT)</th>
                </tr>
              </thead>
              <tbody>
                {plants.map((p: any, i: number) => (
                  <tr key={p.id || i} className="border-t border-slate-700">
                    <td className="py-1.5">{i + 1}</td>
                    <td className="py-1.5">{p.name || p.id}</td>
                    <td className="py-1.5 text-cyan-400">{p.cop?.toFixed(2) || '--'}</td>
                    <td className="py-1.5">{p.carbon_per_rt?.toFixed(2) || '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
