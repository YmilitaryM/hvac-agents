import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import KpiCard from '../components/KpiCard';
import Modal from '../components/Modal';
import { fetchWorkOrders, createWorkOrder, transitionWorkOrder, type WorkOrder } from '../api/workorders';

const VALID_TRANSITIONS: Record<string, string[]> = {
  open: ['acknowledged', 'rejected'],
  acknowledged: ['in_progress', 'rejected'],
  in_progress: ['resolved'],
  resolved: ['closed', 'in_progress'],
  closed: [],
  rejected: [],
};

export default function WorkOrders() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showTransition, setShowTransition] = useState<WorkOrder | null>(null);
  const [transitionNote, setTransitionNote] = useState('');
  const [selectedDetail, setSelectedDetail] = useState<WorkOrder | null>(null);

  const [woEdgeId, setWoEdgeId] = useState('');
  const [woEquipId, setWoEquipId] = useState('');
  const [woSeverity, setWoSeverity] = useState('warning');
  const [woTitle, setWoTitle] = useState('');
  const [woDesc, setWoDesc] = useState('');

  const WO_STATUS_LABELS: Record<string, string> = {
    open: t('workorders.pending'),
    acknowledged: t('workorders.acknowledged'),
    in_progress: t('workorders.inProgress'),
    resolved: t('workorders.resolved'),
    closed: t('workorders.closed'),
    rejected: t('workorders.rejected'),
  };

  const WO_SEVERITY_LABELS: Record<string, string> = {
    critical: t('workorders.critical'),
    warning: t('workorders.warning'),
    info: t('workorders.info'),
  };

  const WO_TRANSITION_LABELS: Record<string, string> = {
    acknowledged: t('workorders.acknowledgeAction'),
    in_progress: t('workorders.startAction'),
    resolved: t('workorders.resolveAction'),
    closed: t('workorders.closeAction'),
    rejected: t('workorders.rejectAction'),
  };

  function statusLabel(s: string) {
    return WO_STATUS_LABELS[s] || s;
  }

  function statusBadge(s: string) {
    const colors: Record<string, string> = {
      open: 'bg-blue-600',
      acknowledged: 'bg-purple-600',
      in_progress: 'bg-yellow-500 text-black',
      resolved: 'bg-green-600',
      closed: 'bg-slate-600',
      rejected: 'bg-red-600',
    };
    return `px-2 py-0.5 rounded-full text-xs font-medium text-white ${colors[s] || 'bg-slate-600'}`;
  }

  function severityLabel(s: string) {
    return WO_SEVERITY_LABELS[s] || s;
  }

  function severityBadge(s: string) {
    const colors: Record<string, string> = {
      critical: 'bg-red-600',
      warning: 'bg-yellow-500 text-black',
      info: 'bg-blue-600',
    };
    return `px-2 py-0.5 rounded text-xs font-medium text-white ${colors[s] || 'bg-slate-600'}`;
  }

  function transitionActionLabel(ns: string) {
    return WO_TRANSITION_LABELS[ns] || ns;
  }

  function WoCard({ wo, onDetail, onTransition }: {
    wo: WorkOrder;
    onDetail: (wo: WorkOrder) => void;
    onTransition: (wo: WorkOrder) => void;
  }) {
    const nextStates = VALID_TRANSITIONS[wo.status] || [];
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3">
        <div className="flex items-center justify-between mb-1">
          <button onClick={() => onDetail(wo)} className="text-cyan-400 hover:underline text-sm text-left font-medium">
            {wo.title}
          </button>
          <span className={severityBadge(wo.severity)}>{severityLabel(wo.severity)}</span>
        </div>
        <div className="flex gap-2 text-xs text-slate-400 mb-2">
          <span className="font-mono">{wo.id?.slice(0, 8)}</span>
          <span>{wo.equipment_id}</span>
          <span className={statusBadge(wo.status)}>{statusLabel(wo.status)}</span>
        </div>
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{new Date(wo.created_at).toLocaleString()}</span>
          {nextStates.length > 0 && (
            <button onClick={() => onTransition(wo)} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs">
              {transitionActionLabel(nextStates[0])}
            </button>
          )}
        </div>
      </div>
    );
  }

  const { data, isLoading } = useQuery({
    queryKey: ['workorders', { status: statusFilter, severity: severityFilter, search }],
    queryFn: () => fetchWorkOrders({
      status: statusFilter || undefined,
      severity: severityFilter || undefined,
      search: search || undefined,
    }),
    refetchInterval: 15000,
  });

  const orders: WorkOrder[] = data?.work_orders || [];

  const counts = {
    open: orders.filter(o => o.status === 'open').length,
    acknowledged: orders.filter(o => o.status === 'acknowledged').length,
    in_progress: orders.filter(o => o.status === 'in_progress').length,
    resolved: orders.filter(o => o.status === 'resolved').length,
    closed_rejected: orders.filter(o => o.status === 'closed' || o.status === 'rejected').length,
  };

  const createMut = useMutation({
    mutationFn: createWorkOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workorders'] });
      setShowCreate(false);
      setWoEdgeId(''); setWoEquipId(''); setWoSeverity('warning'); setWoTitle(''); setWoDesc('');
    },
  });

  const transitionMut = useMutation({
    mutationFn: ({ woId, toStatus, note }: { woId: string; toStatus: string; note?: string }) =>
      transitionWorkOrder(woId, toStatus, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workorders'] });
      setShowTransition(null);
      setTransitionNote('');
    },
  });

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">{t('workorders.title')}</h2>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <KpiCard label={t('workorders.pending')} value={String(counts.open)} color="text-blue-400" />
        <KpiCard label={t('workorders.acknowledged')} value={String(counts.acknowledged)} color="text-purple-400" />
        <KpiCard label={t('workorders.inProgress')} value={String(counts.in_progress)} color="text-yellow-400" />
        <KpiCard label={t('workorders.resolved')} value={String(counts.resolved)} color="text-green-400" />
        <KpiCard label={t('workorders.closedRejected')} value={String(counts.closed_rejected)} color="text-slate-400" />
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="text"
          placeholder={t('workorders.searchPlaceholder')}
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-400 flex-1 min-w-[200px]"
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
          <option value="">{t('common.allStatus')}</option>
          <option value="open">{t('workorders.pending')}</option>
          <option value="acknowledged">{t('workorders.acknowledged')}</option>
          <option value="in_progress">{t('workorders.inProgress')}</option>
          <option value="resolved">{t('workorders.resolved')}</option>
          <option value="closed">{t('workorders.closed')}</option>
          <option value="rejected">{t('workorders.rejected')}</option>
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
          <option value="">{t('common.allLevels')}</option>
          <option value="critical">{t('workorders.critical')}</option>
          <option value="warning">{t('workorders.warning')}</option>
          <option value="info">{t('workorders.info')}</option>
        </select>
        <button onClick={() => setShowCreate(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium">
          {t('workorders.createWO')}
        </button>
      </div>

      <div className="hidden md:block bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-left">
              <th className="px-4 py-3">{t('workorders.id')}</th>
              <th className="px-4 py-3">{t('workorders.title')}</th>
              <th className="px-4 py-3">{t('workorders.equipment')}</th>
              <th className="px-4 py-3">{t('workorders.severity')}</th>
              <th className="px-4 py-3">{t('workorders.status')}</th>
              <th className="px-4 py-3">{t('workorders.source')}</th>
              <th className="px-4 py-3">{t('workorders.createdAt')}</th>
              <th className="px-4 py-3">{t('workorders.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">{t('common.loading')}</td></tr>
            ) : orders.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">{t('common.notFoundWorkOrder')}</td></tr>
            ) : (
              orders.map(wo => {
                const nextStates = VALID_TRANSITIONS[wo.status] || [];
                return (
                  <tr key={wo.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="px-4 py-3 font-mono text-xs">{wo.id?.slice(0, 8)}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => setSelectedDetail(wo)} className="text-cyan-400 hover:underline text-left">
                        {wo.title}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs">{wo.equipment_id}</td>
                    <td className="px-4 py-3"><span className={severityBadge(wo.severity)}>{severityLabel(wo.severity)}</span></td>
                    <td className="px-4 py-3"><span className={statusBadge(wo.status)}>{statusLabel(wo.status)}</span></td>
                    <td className="px-4 py-3 text-xs"><span className={`px-1.5 py-0.5 rounded text-xs ${wo.source === 'auto' ? 'bg-purple-900 text-purple-300' : 'bg-slate-700 text-slate-300'}`}>{wo.source === 'auto' ? t('workorders.auto') : t('workorders.manual')}</span></td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{new Date(wo.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 flex-wrap">
                        {nextStates.map(ns => (
                          <button
                            key={ns}
                            onClick={() => { setShowTransition(wo); setTransitionNote(''); }}
                            className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded"
                          >
                            {transitionActionLabel(ns)}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="md:hidden space-y-2">
        {isLoading ? (
          <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
        ) : orders.length === 0 ? (
          <div className="text-slate-500 text-center py-8">{t('common.notFoundWorkOrder')}</div>
        ) : (
          orders.map(wo => (
            <WoCard
              key={wo.id}
              wo={wo}
              onDetail={setSelectedDetail}
              onTransition={(w) => { setShowTransition(w); setTransitionNote(''); }}
            />
          ))
        )}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={t('workorders.createWOTitle')}>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">{t('workorders.edgeId')}</label>
            <input value={woEdgeId} onChange={e => setWoEdgeId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{t('workorders.equipmentId')}</label>
            <input value={woEquipId} onChange={e => setWoEquipId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{t('workorders.severityLabel')}</label>
            <select value={woSeverity} onChange={e => setWoSeverity(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
              <option value="critical">{t('workorders.critical')}</option>
              <option value="warning">{t('workorders.warning')}</option>
              <option value="info">{t('workorders.info')}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{t('workorders.titleLabel')}</label>
            <input value={woTitle} onChange={e => setWoTitle(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{t('workorders.description')}</label>
            <textarea value={woDesc} onChange={e => setWoDesc(e.target.value)} rows={3} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">{t('common.cancel')}</button>
          <button
            onClick={() => createMut.mutate({ edge_id: woEdgeId, equipment_id: woEquipId, severity: woSeverity, title: woTitle, description: woDesc })}
            disabled={createMut.isPending || !woEdgeId || !woEquipId || !woTitle}
            className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
          >
            {createMut.isPending ? t('common.creating') : t('common.create')}
          </button>
        </div>
        {createMut.isError && (
          <p className="text-red-400 text-xs mt-2">{(createMut.error as Error).message}</p>
        )}
      </Modal>

      <Modal open={!!showTransition} onClose={() => setShowTransition(null)} title={t('workorders.changeStatusTitle')} maxWidth="max-w-sm">
        {showTransition && (
          <>
            <p className="text-sm text-slate-400 mb-3">{showTransition.title} &mdash; {t('workorders.current')}: <span className={statusBadge(showTransition.status)}>{statusLabel(showTransition.status)}</span></p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">{t('workorders.availableActions')}:</label>
                <div className="flex gap-2 flex-wrap">
                  {(VALID_TRANSITIONS[showTransition.status] || []).map(ns => (
                    <button
                      key={ns}
                      onClick={() => transitionMut.mutate({ woId: showTransition.id, toStatus: ns, note: transitionNote || undefined })}
                      disabled={transitionMut.isPending}
                      className="px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
                    >
                      &rarr; {transitionActionLabel(ns)}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">{t('workorders.note')}</label>
                <input value={transitionNote} onChange={e => setTransitionNote(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            {transitionMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(transitionMut.error as Error).message}</p>
            )}
          </>
        )}
      </Modal>

      <Modal open={!!selectedDetail} onClose={() => setSelectedDetail(null)} title={t('workorders.detailTitle')} maxWidth="max-w-lg">
        {selectedDetail && (
          <>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.id')}</dt><dd className="font-mono">{selectedDetail.id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.title')}</dt><dd>{selectedDetail.title}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.equipment')}</dt><dd>{selectedDetail.equipment_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.edge')}</dt><dd>{selectedDetail.edge_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.severity')}</dt><dd><span className={severityBadge(selectedDetail.severity)}>{severityLabel(selectedDetail.severity)}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.status')}</dt><dd><span className={statusBadge(selectedDetail.status)}>{statusLabel(selectedDetail.status)}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.source')}</dt><dd>{selectedDetail.source === 'auto' ? t('workorders.auto') : t('workorders.manual')}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.assignedTo')}</dt><dd>{selectedDetail.assigned_to || '--'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.createdAt')}</dt><dd>{new Date(selectedDetail.created_at).toLocaleString()}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.updatedAt')}</dt><dd>{new Date(selectedDetail.updated_at).toLocaleString()}</dd></div>
              {selectedDetail.resolved_at && <div className="flex justify-between"><dt className="text-slate-400">{t('workorders.resolvedAt')}</dt><dd>{new Date(selectedDetail.resolved_at).toLocaleString()}</dd></div>}
            </dl>
            {selectedDetail.description && (
              <div className="mt-4">
                <h4 className="text-xs text-slate-400 mb-1">{t('workorders.descriptionLabel')}</h4>
                <p className="text-sm text-slate-300 bg-slate-700/50 rounded p-3">{selectedDetail.description}</p>
              </div>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}
