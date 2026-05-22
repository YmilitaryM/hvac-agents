import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchDailyReport } from '../api/reports';
import { fetchBenchmarking } from '../api/reports';
import KpiCard from '../components/KpiCard';

export default function Reports() {
  const { t } = useTranslation();
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
        <h2 className="text-xl font-bold">{t('reports.title')}</h2>
        <input
          value={plantId}
          onChange={e => setPlantId(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-32 text-sm"
          placeholder="Plant ID"
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <KpiCard label={t('reports.dailyAvgCop')} value={kpi.avg_cop?.toFixed(2) || '--'} color="text-cyan-400" />
        <KpiCard label={t('reports.totalEnergy')} value={kpi.total_energy_kwh?.toFixed(0) || '--'} />
        <KpiCard label={t('reports.carbonEmissions')} value={kpi.carbon_kg?.toFixed(0) || '--'} />
        <KpiCard label={t('reports.electricityCost')} value={kpi.electricity_cost?.toFixed(0) || '--'} />
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
        <h3 className="text-sm text-slate-400 uppercase mb-3">{t('reports.strategyStats')}</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={[
            { name: t('reports.defaultStrategy'), count: 45 },
            { name: t('reports.energySaveStrategy'), count: 32 },
            { name: t('reports.comfortStrategy'), count: 18 },
            { name: t('reports.drlStrategy'), count: 5 },
          ]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
            <Bar dataKey="count" fill="#38bdf8" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">{t('reports.optimizationSuggestions')}</h3>
          {recommendations.length === 0 ? (
            <div className="text-slate-500 text-sm">
              <p>{t('reports.noSuggestions')}</p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-slate-400">
                <li>{t('reports.suggestion1')}</li>
                <li>{t('reports.suggestion2')}</li>
                <li>{t('reports.suggestion3')}</li>
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
          <h3 className="font-medium mb-3">{t('reports.benchmarking')}</h3>
          {plants.length === 0 ? (
            <div className="text-slate-500 text-sm">
              <table className="w-full text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="text-left py-1">{t('reports.rank')}</th>
                    <th className="text-left py-1">{t('reports.plant')}</th>
                    <th className="text-left py-1">{t('reports.cop')}</th>
                    <th className="text-left py-1">{t('reports.energyIntensity')}</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { rank: 1, name: 'Plant A (Beijing)', cop: 5.2, intensity: '0.68 kW/RT' },
                    { rank: 2, name: 'Plant B (Shanghai)', cop: 4.8, intensity: '0.73 kW/RT' },
                    { rank: 3, name: 'Plant C (Guangzhou)', cop: 4.3, intensity: '0.82 kW/RT' },
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
                  <th className="text-left py-1">{t('reports.rank')}</th>
                  <th className="text-left py-1">{t('reports.plant')}</th>
                  <th className="text-left py-1">{t('reports.cop')}</th>
                  <th className="text-left py-1">{t('reports.carbonIntensity')}</th>
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
