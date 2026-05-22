import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../../api/health';
import { downloadFile } from '../../api/client';
import { useState } from 'react';

export default function RULPrediction() {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['health-rul', 1],
    queryFn: () => healthApi.getRUL(1),
    refetchInterval: 120000,
  });
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadFile('/api/health/rul/download?plant_id=1', 'RUL_Prediction.xlsx');
    } catch (e) {
      alert(t('healthRUL.downloadFailed') + ': ' + (e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading || !data) return <div className="p-6 text-gray-400">{t('common.loading')}</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('healthRUL.title')}</h1>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
        >
          {downloading ? t('healthRUL.downloading') : t('healthRUL.exportExcel')}
        </button>
      </div>
      <div className="space-y-4">
        {data.items.map((item, i) => {
          const days = Math.round(item.predicted_hours / 24);
          const daysLo = Math.round(item.ci_lo / 24);
          const daysHi = Math.round(item.ci_hi / 24);
          const urgency = days < 30 ? 'urgent' : days < 90 ? 'warning' : 'normal';
          const borderColor = urgency === 'urgent' ? 'border-red-500' : urgency === 'warning' ? 'border-yellow-500' : 'border-green-500';
          return (
            <div key={i} className={`bg-white rounded-lg shadow p-4 border-l-4 ${borderColor}`}>
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-semibold">{t('healthRUL.device')} {item.equipment_id} - {item.component}</div>
                  <div className="text-sm text-gray-500">{t('healthRUL.model')}: {item.degradation_model}</div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold">{days} <span className="text-base text-gray-500">{t('healthRUL.days')}</span></div>
                  <div className="text-xs text-gray-400">{t('healthRUL.ciRange')}: {daysLo}-{daysHi} {t('healthRUL.days')}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
