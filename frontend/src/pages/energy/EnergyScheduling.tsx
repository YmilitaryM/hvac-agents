import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { energyApi } from '../../api/energy';

export default function EnergyScheduling() {
  const { t } = useTranslation();
  const [result, setResult] = useState<unknown>(null);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">{t('energyScheduling.title')}</h1>
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">{t('energyScheduling.touPeriods')}</h2>
        <div className="grid grid-cols-3 gap-4 text-center mb-6">
          <div className="bg-green-50 rounded p-3"><div className="text-sm text-gray-500">{t('energyScheduling.valleyPeriod')}</div><div className="text-xl font-bold text-green-600">0.35 {t('energyScheduling.priceUnit')}</div></div>
          <div className="bg-yellow-50 rounded p-3"><div className="text-sm text-gray-500">{t('energyScheduling.flatPeriod')}</div><div className="text-xl font-bold text-yellow-600">0.75 {t('energyScheduling.priceUnit')}</div></div>
          <div className="bg-red-50 rounded p-3"><div className="text-sm text-gray-500">{t('energyScheduling.peakPeriod')}</div><div className="text-xl font-bold text-red-600">1.15 {t('energyScheduling.priceUnit')}</div></div>
        </div>
        <button
          onClick={async () => { const r = await energyApi.optimizeDemand(1); setResult(r); }}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
        >
          {t('energyScheduling.runOptimization')}
        </button>
        {result && <pre className="mt-4 p-4 bg-gray-50 rounded text-sm">{JSON.stringify(result, null, 2)}</pre>}
      </div>
    </div>
  );
}
