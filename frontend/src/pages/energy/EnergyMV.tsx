import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { downloadFile } from '../../api/client';
import { useState } from 'react';

export default function EnergyMV() {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['energy-mv', 1],
    queryFn: () => energyApi.getMv(1),
  });
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadFile('/api/energy/mv/download?plant_id=1', 'MV_Verification.xlsx');
    } catch (e) {
      alert(t('energyMV.downloadFailed') + ': ' + (e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading || !data) return <div className="p-6 text-gray-400">{t('common.loading')}</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('energyMV.title')}</h1>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
        >
          {downloading ? t('common.downloading') : t('energyMV.exportExcel')}
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">{t('energyMV.savings')}</div>
          <div className="text-2xl font-bold text-green-600">{data.savings_kwh.toLocaleString()} kWh</div>
          <div className="text-sm text-gray-400">{data.savings_pct}%</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">{t('energyMV.coalSaved')}</div>
          <div className="text-2xl font-bold">{data.coal_equivalent_tons} t</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">{t('energyMV.carbonReduction')}</div>
          <div className="text-2xl font-bold text-cyan-600">{data.carbon_reduction_kg.toLocaleString()} kg</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">{t('energyMV.cvRmse')}</div>
          <div className={`text-2xl font-bold ${data.cv_rmse_pct <= 20 ? 'text-green-600' : 'text-red-600'}`}>{data.cv_rmse_pct}%</div>
          <div className="text-sm text-gray-400">{data.cv_rmse_pct <= 20 ? t('energyMV.ashraeCompliant') : t('energyMV.exceeded')}</div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">{t('energyMV.nationalStandard')}</h2>
          <div className="space-y-2">
            <div className={`flex items-center gap-2 ${data.compliant_gb28750 ? 'text-green-600' : 'text-red-600'}`}>
              {data.compliant_gb28750 ? '✓' : '✗'} {t('energyMV.gbVerified')}
            </div>
            <div className={`flex items-center gap-2 ${data.compliant_ashrae_g14 ? 'text-green-600' : 'text-red-600'}`}>
              {data.compliant_ashrae_g14 ? '✓' : '✗'} {t('energyMV.ashraeVerified')}
            </div>
            <div className={`flex items-center gap-2 ${Math.abs(data.nmbe_pct) <= 5 ? 'text-green-600' : 'text-red-600'}`}>
              {Math.abs(data.nmbe_pct) <= 5 ? '✓' : '✗'} {t('energyMV.nmbeCheck')}: {data.nmbe_pct}% (&le;&plusmn;5%)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
