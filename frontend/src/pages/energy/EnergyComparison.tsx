import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { downloadFile } from '../../api/client';
import { useState } from 'react';

export default function EnergyComparison() {
  const [period, setPeriod] = useState('month');
  const { data, isLoading } = useQuery({
    queryKey: ['energy-comparison', 1, period],
    queryFn: () => energyApi.getComparison(1, period),
  });
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadFile(`/api/energy/comparison/download?plant_id=1&period=${period}`, `能耗对比_${period}.xlsx`);
    } catch (e) {
      alert('下载失败: ' + (e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">能耗对比</h1>
        <div className="flex gap-2">
          <select value={period} onChange={(e) => setPeriod(e.target.value)}
                  className="border rounded px-3 py-2">
            <option value="day">日</option>
            <option value="week">周</option>
            <option value="month">月</option>
            <option value="year">年</option>
          </select>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
          >
            {downloading ? '下载中...' : '导出Excel'}
          </button>
        </div>
      </div>
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">本期总能耗</div>
            <div className="text-2xl font-bold">{data.current.total_kwh.toLocaleString()} kWh</div>
            <div className="text-sm text-gray-400">平均COP: {data.current.avg_cop}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">环比变化</div>
            <div className={`text-2xl font-bold ${data.mom_change_pct.total_kwh >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              {data.mom_change_pct.total_kwh >= 0 ? '+' : ''}{data.mom_change_pct.total_kwh}%
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">同比变化</div>
            <div className={`text-2xl font-bold ${data.yoy_change_pct.total_kwh >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              {data.yoy_change_pct.total_kwh >= 0 ? '+' : ''}{data.yoy_change_pct.total_kwh}%
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
