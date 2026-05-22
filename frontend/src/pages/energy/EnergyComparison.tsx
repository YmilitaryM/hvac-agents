import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { downloadFile } from '../../api/client';
import { useState } from 'react';

export default function EnergyComparison() {
  const { t } = useTranslation();
  const [period, setPeriod] = useState('month');
  const { data, isLoading } = useQuery({
    queryKey: ['energy-comparison', 1, period],
    queryFn: () => energyApi.getComparison(1, period),
  });
  const [downloading, setDownloading] = useState(false);

  const PERIOD_LABELS: Record<string, string> = {
    day: t('energyComparison.day'),
    week: t('energyComparison.week'),
    month: t('energyComparison.month'),
    year: t('energyComparison.year'),
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadFile(`/api/energy/comparison/download?plant_id=1&period=${period}`, `Energy_Comparison_${period}.xlsx`);
    } catch (e) {
      alert(t('energyComparison.downloadFailed') + ': ' + (e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading) return <div className="p-6 text-gray-400">{t('common.loading')}</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('energyComparison.title')}</h1>
        <div className="flex gap-2">
          <select value={period} onChange={(e) => setPeriod(e.target.value)}
                  className="border rounded px-3 py-2">
            {Object.entries(PERIOD_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
          >
            {downloading ? t('energyComparison.downloading') : t('energyComparison.exportExcel')}
          </button>
        </div>
      </div>
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">{t('energyComparison.currentPeriodEnergy')}</div>
            <div className="text-2xl font-bold">{data.current.total_kwh.toLocaleString()} kWh</div>
            <div className="text-sm text-gray-400">{t('energyComparison.avgCop')}: {data.current.avg_cop}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">{t('energyComparison.momChange')}</div>
            <div className={`text-2xl font-bold ${data.mom_change_pct.total_kwh >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              {data.mom_change_pct.total_kwh >= 0 ? '+' : ''}{data.mom_change_pct.total_kwh}%
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">{t('energyComparison.yoyChange')}</div>
            <div className={`text-2xl font-bold ${data.yoy_change_pct.total_kwh >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              {data.yoy_change_pct.total_kwh >= 0 ? '+' : ''}{data.yoy_change_pct.total_kwh}%
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
