import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

interface OverrideEntry {
  override_id: string;
  device_id: string;
  override_type: string;
  value: number;
  reason: string;
  created_at: number;
  expires_at: number;
  active: boolean;
}

async function fetchOverrides(activeOnly: boolean): Promise<{ overrides: OverrideEntry[] }> {
  const resp = await apiClient.get(`/api/override?active_only=${activeOnly}`);
  return resp.data;
}

async function createOverride(data: {
  device_id: string;
  override_type: string;
  value: number;
  reason: string;
  timeout_minutes: number;
}): Promise<OverrideEntry> {
  const resp = await apiClient.post('/api/override', data);
  return resp.data;
}

async function cancelOverride(overrideId: string): Promise<void> {
  await apiClient.delete(`/api/override/${overrideId}`);
}

async function revertOverride(overrideId: string): Promise<void> {
  await apiClient.post(`/api/override/${overrideId}/revert`);
}

export default function ManualOverride() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    device_id: '',
    override_type: 'setpoint',
    value: 0,
    reason: '',
    timeout_minutes: 30,
  });

  const OVERRIDE_LABELS: Record<string, string> = {
    setpoint: t('override.setpoint'),
    chiller_on: t('override.chillerOn'),
    chiller_off: t('override.chillerOff'),
    pump_speed: t('override.pumpSpeed'),
    tower_fan: t('override.towerFan'),
    valve_position: t('override.valvePosition'),
    strategy_switch: t('override.strategySwitch'),
  };

  const { data, isLoading } = useQuery({
    queryKey: ['overrides'],
    queryFn: () => fetchOverrides(true),
    refetchInterval: 5000,
  });

  const createMut = useMutation({
    mutationFn: createOverride,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['overrides'] });
      setShowForm(false);
    },
  });

  const cancelMut = useMutation({
    mutationFn: cancelOverride,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['overrides'] }),
  });

  const revertMut = useMutation({
    mutationFn: revertOverride,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['overrides'] }),
  });

  const overrides = data?.overrides || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">{t('override.title')}</h2>
        <button
          onClick={() => setShowForm(v => !v)}
          className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded text-sm"
        >
          {showForm ? t('common.cancel') : t('override.newOverride')}
        </button>
      </div>

      {showForm && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">{t('override.deviceId')}</label>
              <input
                className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                placeholder={t('override.placeholderDeviceId')}
                value={form.device_id}
                onChange={e => setForm(f => ({ ...f, device_id: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">{t('override.overrideType')}</label>
              <select
                className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                value={form.override_type}
                onChange={e => setForm(f => ({ ...f, override_type: e.target.value }))}
              >
                {Object.entries(OVERRIDE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">{t('override.setpointValue')}</label>
              <input
                type="number"
                className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                value={form.value}
                onChange={e => setForm(f => ({ ...f, value: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">{t('override.autoRestore')}</label>
              <input
                type="number"
                className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                value={form.timeout_minutes}
                onChange={e => setForm(f => ({ ...f, timeout_minutes: Number(e.target.value) }))}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-slate-400 mb-1">{t('override.reason')}</label>
              <input
                className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                placeholder={t('override.reasonPlaceholder')}
                value={form.reason}
                onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
              />
            </div>
          </div>
          <button
            onClick={() => createMut.mutate(form)}
            disabled={!form.device_id || createMut.isPending}
            className="mt-4 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white px-4 py-2 rounded text-sm"
          >
            {createMut.isPending ? t('common.submitting') : t('override.confirmOverride')}
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="text-slate-400">{t('common.loading')}</div>
      ) : overrides.length === 0 ? (
        <div className="text-slate-500 text-center py-12">{t('common.noActiveOverrides')}</div>
      ) : (
        <div className="space-y-2">
          {overrides.map((o: OverrideEntry) => (
            <div
              key={o.override_id}
              className="bg-slate-800 border border-slate-700 rounded-lg p-4 flex items-start justify-between"
            >
              <div>
                <div className="flex gap-2 items-center">
                  <span className="font-medium">{o.device_id}</span>
                  <span className="text-xs bg-blue-700 text-blue-200 px-2 py-0.5 rounded">
                    {OVERRIDE_LABELS[o.override_type] || o.override_type}
                  </span>
                  <span className="text-sm text-slate-400">&rarr; {o.value}</span>
                </div>
                {o.reason && (
                  <div className="text-xs text-slate-500 mt-1">{t('override.reason')}: {o.reason}</div>
                )}
                <div className="text-xs text-slate-500 mt-1">
                  {t('override.created')}: {new Date(o.created_at * 1000).toLocaleString()}
                  {o.expires_at < 1e12 && (
                    <span className="ml-3">
                      {t('override.expires')}: {new Date(o.expires_at * 1000).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => revertMut.mutate(o.override_id)}
                  className="text-xs bg-yellow-700 hover:bg-yellow-600 px-3 py-1 rounded"
                >
                  {t('override.restore')}
                </button>
                <button
                  onClick={() => cancelMut.mutate(o.override_id)}
                  className="text-xs bg-red-700 hover:bg-red-600 px-3 py-1 rounded"
                >
                  {t('override.cancel')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
