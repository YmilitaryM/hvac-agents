import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAlerts, acknowledgeAlert } from '../api/monitoring';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-600 text-white',
  warning: 'bg-yellow-500 text-black',
  info: 'bg-blue-500 text-white',
};

export default function Alerts() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<{ severity?: string; ack?: boolean }>({});

  const { data, isLoading } = useQuery({
    queryKey: ['alerts', filter],
    queryFn: () => fetchAlerts({ severity: filter.severity, acknowledged: filter.ack }),
    refetchInterval: 10000,
  });

  const ackMut = useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  });

  const alerts = data?.alerts || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">{t('alerts.title')}</h2>
        <div className="flex gap-2">
          <select
            className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm"
            value={filter.severity || ''}
            onChange={e => setFilter(f => ({ ...f, severity: e.target.value || undefined }))}
          >
            <option value="">{t('alerts.allLevels')}</option>
            <option value="critical">{t('alerts.critical')}</option>
            <option value="warning">{t('alerts.warning')}</option>
            <option value="info">{t('alerts.info')}</option>
          </select>
          <select
            className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm"
            value={filter.ack === undefined ? '' : String(filter.ack)}
            onChange={e => {
              const v = e.target.value;
              setFilter(f => ({ ...f, ack: v === '' ? undefined : v === 'true' }));
            }}
          >
            <option value="">{t('alerts.allStatus')}</option>
            <option value="false">{t('alerts.unacknowledged')}</option>
            <option value="true">{t('alerts.acknowledged')}</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="text-slate-400">{t('common.loading')}</div>
      ) : alerts.length === 0 ? (
        <div className="text-slate-500 text-center py-12">{t('alerts.noAlerts')}</div>
      ) : (
        <div className="space-y-2">
          {alerts.map((a: any) => (
            <div
              key={a.id}
              className={`bg-slate-800 border border-slate-700 rounded-lg p-4 flex items-start justify-between ${
                a.acknowledged ? 'opacity-60' : ''
              }`}
            >
              <div className="flex gap-3 items-start">
                <span className={`px-2 py-0.5 rounded text-xs font-medium mt-0.5 ${SEVERITY_COLORS[a.severity] || 'bg-slate-600'}`}>
                  {a.severity}
                </span>
                <div>
                  <div className="font-medium">{a.message || a.rule_name}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    {a.device_id && <span className="mr-3">{t('alerts.device')}: {a.device_id}</span>}
                    <span>{new Date(a.timestamp || a.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              {!a.acknowledged && (
                <button
                  onClick={() => ackMut.mutate(a.id)}
                  className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded shrink-0"
                >
                  {t('alerts.acknowledge')}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
