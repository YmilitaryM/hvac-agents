import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function EnergyDemand() {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['energy-demand', 1],
    queryFn: () => energyApi.getDemand(1),
    refetchInterval: 30000,
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">{t('common.loading')}</div>;

  const chartData = data.trend.map((v, i) => ({ idx: i, kw: v }));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">{t('energyDemand.title')}</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">{t('energyDemand.currentDemand')}</div>
          <div className="text-3xl font-bold">{data.current_kw} <span className="text-base text-gray-500">kW</span></div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">{t('energyDemand.predictedPeak')}</div>
          <div className={`text-3xl font-bold ${data.warning ? 'text-red-600' : 'text-green-600'}`}>
            {data.predicted_peak_kw} <span className="text-base text-gray-500">kW</span>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">{t('energyDemand.demandLimit')}</div>
          <div className="text-3xl font-bold text-blue-600">{data.demand_limit_kw} <span className="text-base text-gray-500">kW</span></div>
        </div>
      </div>
      {data.warning && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">{t('energyDemand.demandWarning')}</div>
      )}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">{t('energyDemand.demandTrend')}</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="idx" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="kw" stroke="#ea580c" name="kW" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
