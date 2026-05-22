import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../../api/health';

const statusColor = (status: string) => {
  switch (status) {
    case 'healthy': return 'bg-green-100 text-green-800';
    case 'degrading': return 'bg-yellow-100 text-yellow-800';
    case 'critical': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

export default function HealthDashboard() {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['health-dashboard', 1],
    queryFn: () => healthApi.getDashboard(1),
    refetchInterval: 30000,
  });

  const STATUS_LABELS: Record<string, string> = {
    healthy: t('healthDashboard.healthy'),
    degrading: t('healthDashboard.degrading'),
    critical: t('healthDashboard.critical'),
  };

  const TREND_LABELS: Record<string, string> = {
    down: t('healthDashboard.trendDown'),
    up: t('healthDashboard.trendUp'),
    stable: t('healthDashboard.trendStable'),
  };

  if (isLoading || !data) return <div className="p-6 text-gray-400">{t('common.loading')}</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">{t('healthDashboard.title')}</h1>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4">
          <div className="text-5xl font-bold text-blue-600">{data.overall_health}</div>
          <div className="text-gray-500">{t('healthDashboard.overallHealth')}</div>
        </div>
      </div>
      <div className="space-y-3">
        {data.equipment_health.map((eq) => (
          <div key={eq.equipment_id} className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
            <div>
              <div className="font-semibold">{eq.name}</div>
              <div className="text-sm text-gray-500">{t('nav.health')}: {TREND_LABELS[eq.trend] || '--'}</div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-2xl font-bold">{eq.overall_score}</div>
              <span className={`px-2 py-1 rounded text-xs ${statusColor(eq.status)}`}>
                {STATUS_LABELS[eq.status] || eq.status}
              </span>
            </div>
          </div>
        ))}
      </div>
      {data.top_degrading.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">{t('healthDashboard.degradationTopN')}</h2>
          {data.top_degrading.map((d, i) => (
            <div key={i} className="flex justify-between py-2 border-b last:border-0">
              <span>{d.equipment_name} - {d.component}</span>
              <span className="text-red-600">{t('healthDashboard.degradationRate')} {d.degradation_rate}/{t('healthRUL.days')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
