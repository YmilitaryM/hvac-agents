import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { useState } from 'react';

export default function EnergyReports() {
  const [period, setPeriod] = useState('day');
  const { data } = useQuery({
    queryKey: ['energy-reports', 1, period],
    queryFn: () => energyApi.getReports(1, period),
  });
  const [generating, setGenerating] = useState(false);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">能源报告</h1>
      <div className="flex gap-2 flex-wrap">
        {(['day', 'week', 'month', 'year'] as const).map((p) => (
          <button key={p} onClick={() => setPeriod(p)} className={`px-4 py-2 rounded ${period === p ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
            {p === 'day' ? '日报' : p === 'week' ? '周报' : p === 'month' ? '月报' : '年报'}
          </button>
        ))}
      </div>
      <button
        onClick={async () => { setGenerating(true); await energyApi.generateReport(1, period, 'daily'); setGenerating(false); }}
        disabled={generating}
        className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {generating ? '生成中...' : '导出报告'}
      </button>
      {data && <pre className="bg-gray-50 rounded p-4 text-sm">{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}
