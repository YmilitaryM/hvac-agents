import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { healthApi } from '../../api/health';

export default function SpectrumAnalysis() {
  const { t } = useTranslation();
  const [equipmentId, setEquipmentId] = useState(1);
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [oilData, setOilData] = useState<unknown>(null);

  const load = async () => {
    setLoading(true);
    const [v, o] = await Promise.all([
      healthApi.getVibration(equipmentId),
      healthApi.getOilAnalysis(equipmentId),
    ]);
    setData(v);
    setOilData(o);
    setLoading(false);
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">{t('healthSpectrum.title')}</h1>
      <div className="flex items-center gap-4">
        <label className="text-sm">{t('healthSpectrum.deviceId')}:</label>
        <input type="number" value={equipmentId} onChange={(e) => setEquipmentId(Number(e.target.value))}
               className="border rounded px-3 py-1 w-24" />
        <button onClick={load} disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          {loading ? t('healthSpectrum.loading') : t('healthSpectrum.loadData')}
        </button>
      </div>
      {data && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">{t('healthSpectrum.vibrationSpectrum')}</h2>
          <pre className="text-xs bg-gray-50 p-4 rounded">{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
      {oilData && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">{t('healthSpectrum.oilAnalysis')}</h2>
          <pre className="text-xs bg-gray-50 p-4 rounded">{JSON.stringify(oilData, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
