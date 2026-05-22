import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { downloadFile } from '../../api/client';
import { useState } from 'react';

export default function EnergyReports() {
  const { t } = useTranslation();
  const [period, setPeriod] = useState('day');
  const { data } = useQuery({
    queryKey: ['energy-reports', 1, period],
    queryFn: () => energyApi.getReports(1, period),
  });
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const PERIOD_LABELS: Record<string, string> = {
    day: t('energyReports.daily'),
    week: t('energyReports.weekly'),
    month: t('energyReports.monthly'),
    year: t('energyReports.yearly'),
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadFile(`/api/energy/reports/download?plant_id=1&period=${period}`, `Energy_Report_${period}.xlsx`);
    } catch (e) {
      alert(t('energyReports.downloadFailed') + ': ' + (e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">{t('energyReports.title')}</h1>
      <div className="flex gap-2 flex-wrap">
        {(['day', 'week', 'month', 'year'] as const).map((p) => (
          <button key={p} onClick={() => setPeriod(p)} className={`px-4 py-2 rounded ${period === p ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
            {PERIOD_LABELS[p]}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          onClick={async () => { setGenerating(true); await energyApi.generateReport(1, period, 'daily'); setGenerating(false); }}
          disabled={generating}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {generating ? t('energyReports.generating') : t('energyReports.generateReport')}
        </button>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50"
        >
          {downloading ? t('energyReports.downloading') : t('energyReports.exportExcel')}
        </button>
      </div>
      {data && <pre className="bg-gray-50 rounded p-4 text-sm">{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}
