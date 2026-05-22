import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchStrategies, updateStrategyStatus, deleteStrategy } from '../api/strategies';
import { getRLStatus, runInference } from '../api/rl';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-600',
  inactive: 'bg-slate-600',
  draft: 'bg-yellow-600',
  archived: 'bg-slate-500',
};

export default function Strategies() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [selected, setSelected] = useState<any>(null);
  const [rlResult, setRlResult] = useState<any>(null);

  const { data: strategies } = useQuery({ queryKey: ['strategies'], queryFn: fetchStrategies });
  const { data: rlStatus } = useQuery({ queryKey: ['rl-status'], queryFn: getRLStatus, refetchInterval: 5000 });

  const statusMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => updateStrategyStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategies'] }),
  });

  const deleteMut = useMutation({
    mutationFn: deleteStrategy,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['strategies'] }); setSelected(null); },
  });

  const items = strategies?.strategies || [];

  const handleInference = async () => {
    const res = await runInference();
    setRlResult(res);
  };

  return (
    <div className="flex gap-4">
      <div className="flex-1">
        <h2 className="text-xl font-bold mb-4">{t('strategies.title')}</h2>

        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          {items.length === 0 ? (
            <div className="text-slate-500 text-center py-12">{t('strategies.noStrategies')}</div>
          ) : (
            items.map((s: any) => (
              <div
                key={s.id}
                onClick={() => setSelected(s)}
                className={`flex items-center justify-between p-3 border-b border-slate-700 cursor-pointer hover:bg-slate-700/50 ${
                  selected?.id === s.id ? 'bg-slate-700' : ''
                }`}
              >
                <div>
                  <div className="font-medium text-sm">{s.name}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {new Date(s.created_at).toLocaleDateString()}
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[s.status] || 'bg-slate-600'}`}>
                  {s.status}
                </span>
              </div>
            ))
          )}
        </div>

        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mt-4">
          <h3 className="font-medium mb-3">{t('strategies.drlTitle')}</h3>
          <div className="grid grid-cols-3 gap-3 mb-3 text-sm">
            <div>
              <div className="text-xs text-slate-400">{t('strategies.trainingStatus')}</div>
              <div>{rlStatus?.training?.status || 'idle'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">{t('strategies.totalSteps')}</div>
              <div>{rlStatus?.model?.total_steps || 0}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">{t('strategies.safetyRate')}</div>
              <div>{rlStatus?.safety?.violation_rate ?? '--'}</div>
            </div>
          </div>
          <button
            onClick={handleInference}
            className="bg-purple-600 hover:bg-purple-500 px-3 py-1.5 rounded text-sm"
          >
            {t('strategies.drlInference')}
          </button>
          {rlResult && (
            <div className="mt-3 p-3 bg-slate-700 rounded text-sm">
              <div className="text-xs text-slate-400 mb-1">{t('strategies.inferenceResult')}</div>
              <div className="grid grid-cols-2 gap-1">
                {Object.entries(rlResult.action || {}).map(([k, v]) => (
                  <div key={k}>{k}: {String(v)}</div>
                ))}
              </div>
              {!rlResult.safety_passed && (
                <div className="text-red-400 text-xs mt-1">{t('strategies.safetyBlocked')}: {rlResult.safety_reason}</div>
              )}
            </div>
          )}
        </div>
      </div>

      {selected && (
        <div className="w-80 bg-slate-800 rounded-lg border border-slate-700 p-4 shrink-0">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium">{selected.name}</h3>
            <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
          <div className="text-xs text-slate-400 mb-2">ID: {selected.id}</div>
          <pre className="bg-slate-900 rounded p-2 text-xs overflow-auto max-h-48 mb-3">
            {JSON.stringify(selected.config, null, 2)}
          </pre>
          <div className="flex gap-2 flex-wrap">
            {selected.status !== 'active' && (
              <button
                onClick={() => statusMut.mutate({ id: selected.id, status: 'active' })}
                className="text-xs bg-green-700 hover:bg-green-600 px-2 py-1 rounded"
              >
                {t('strategies.activate')}
              </button>
            )}
            {selected.status === 'active' && (
              <button
                onClick={() => statusMut.mutate({ id: selected.id, status: 'inactive' })}
                className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
              >
                {t('strategies.deactivate')}
              </button>
            )}
            <button
              onClick={() => statusMut.mutate({ id: selected.id, status: 'archived' })}
              className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded"
            >
              {t('strategies.archive')}
            </button>
            <button
              onClick={() => { if (confirm(t('strategies.confirmDelete'))) deleteMut.mutate(selected.id); }}
              className="text-xs bg-red-700 hover:bg-red-600 px-2 py-1 rounded"
            >
              {t('strategies.delete')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
