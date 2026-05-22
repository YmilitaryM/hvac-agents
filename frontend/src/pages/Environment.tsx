import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';

interface WeatherRow {
  hour: number;
  db_temp: number;
  wb_temp: number;
  month: number;
}

function generateTmySample(): WeatherRow[] {
  const rows: WeatherRow[] = [];
  for (let h = 0; h < 168; h++) {
    const month = Math.floor(h / 730) % 12 + 1;
    const tBase = 28 + 8 * Math.sin((2 * Math.PI * (month - 1)) / 12);
    const tDaily = 6 * Math.sin((2 * Math.PI * (h % 24 - 14)) / 24);
    rows.push({
      hour: h,
      db_temp: Math.round((tBase + tDaily) * 10) / 10,
      wb_temp: Math.round((tBase + tDaily - 7) * 10) / 10,
      month,
    });
  }
  return rows;
}

const TMY_SAMPLE = generateTmySample();

export default function Environment() {
  const { t } = useTranslation();
  const [tmyView, setTmyView] = useState(false);
  const [priceTab, setPriceTab] = useState<'peak' | 'flat' | 'valley'>('peak');

  const { data: envData } = useQuery({
    queryKey: ['env'],
    queryFn: () => fetch('/api/env').then(r => r.json()),
  });

  const PRICE_TABS: Record<string, string> = {
    peak: t('environment.peak'),
    flat: t('environment.flat'),
    valley: t('environment.valley'),
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">{t('environment.title')}</h2>

      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium">{t('environment.weatherData')}</h3>
          <button
            onClick={() => setTmyView(!tmyView)}
            className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded"
          >
            {tmyView ? t('environment.hide') : t('environment.viewTMY')}
          </button>
        </div>
        {tmyView && (
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-slate-400">
                <tr>
                  <th className="text-left py-1">{t('environment.hour')}</th>
                  <th className="text-left py-1">{t('environment.month')}</th>
                  <th className="text-left py-1">{t('environment.dbTemp')}</th>
                  <th className="text-left py-1">{t('environment.wbTemp')}</th>
                </tr>
              </thead>
              <tbody>
                {TMY_SAMPLE.map(r => (
                  <tr key={r.hour} className="border-t border-slate-700">
                    <td className="py-1">{r.hour}</td>
                    <td className="py-1">{r.month}</td>
                    <td className="py-1">{r.db_temp}</td>
                    <td className="py-1">{r.wb_temp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
        <h3 className="font-medium mb-3">{t('environment.electricityPrice')}</h3>
        <div className="flex gap-2 mb-3">
          {(['peak', 'flat', 'valley'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setPriceTab(tab)}
              className={`px-3 py-1 rounded text-sm ${
                priceTab === tab ? 'bg-cyan-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              {PRICE_TABS[tab]}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-700 rounded p-3 text-center">
            <div className="text-xs text-slate-400">{t('environment.peakTime')}</div>
            <div className="text-lg font-bold text-yellow-400">1.20</div>
          </div>
          <div className="bg-slate-700 rounded p-3 text-center">
            <div className="text-xs text-slate-400">{t('environment.flatTime')}</div>
            <div className="text-lg font-bold text-blue-400">0.75</div>
          </div>
          <div className="bg-slate-700 rounded p-3 text-center">
            <div className="text-xs text-slate-400">{t('environment.valleyTime')}</div>
            <div className="text-lg font-bold text-green-400">0.35</div>
          </div>
        </div>
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 className="font-medium mb-3">{t('environment.buildingParams')}</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[
            [t('environment.buildingArea'), '50,000'],
            [t('environment.windowWallRatio'), '0.35'],
            [t('environment.heatTransferCoeff'), '0.45'],
            [t('environment.personDensity'), '0.10'],
            [t('environment.lightingDensity'), '9.0'],
            [t('environment.equipmentDensity'), '15.0'],
            [t('environment.freshAir'), '30'],
            [t('environment.indoorTemp'), '26'],
            [t('environment.indoorHumidity'), '55'],
          ].map(([label, value]) => (
            <div key={label} className="bg-slate-700 rounded p-3">
              <div className="text-xs text-slate-400">{label}</div>
              <div className="font-medium mt-1">{value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
