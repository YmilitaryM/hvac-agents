import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import KpiCard from '../components/KpiCard';
import { fetchWorkOrders, createWorkOrder, transitionWorkOrder, type WorkOrder } from '../api/workorders';

const VALID_TRANSITIONS: Record<string, string[]> = {
  open: ['acknowledged', 'rejected'],
  acknowledged: ['in_progress', 'rejected'],
  in_progress: ['resolved'],
  resolved: ['closed', 'in_progress'],
  closed: [],
  rejected: [],
};

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

function severityBadge(s: string) {
  const colors: Record<string, string> = {
    critical: 'bg-red-600',
    warning: 'bg-yellow-500 text-black',
    info: 'bg-blue-600',
  };
  return `px-2 py-0.5 rounded text-xs font-medium text-white ${colors[s] || 'bg-slate-600'}`;
}

export default function WorkOrders() {
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
      <h2 className="text-xl font-bold mb-4">Work Orders</h2>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <KpiCard label="Open" value={String(counts.open)} color="text-blue-400" />
        <KpiCard label="Acknowledged" value={String(counts.acknowledged)} color="text-purple-400" />
        <KpiCard label="In Progress" value={String(counts.in_progress)} color="text-yellow-400" />
        <KpiCard label="Resolved" value={String(counts.resolved)} color="text-green-400" />
        <KpiCard label="Closed/Rejected" value={String(counts.closed_rejected)} color="text-slate-400" />
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by title or equipment..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-400 flex-1 min-w-[200px]"
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
          <option value="rejected">Rejected</option>
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
          <option value="">All Severity</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <button onClick={() => setShowCreate(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium">
          New Order
        </button>
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-left">
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Equipment</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">Loading...</td></tr>
            ) : orders.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">No work orders found</td></tr>
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
                    <td className="px-4 py-3"><span className={severityBadge(wo.severity)}>{wo.severity}</span></td>
                    <td className="px-4 py-3"><span className={statusBadge(wo.status)}>{wo.status}</span></td>
                    <td className="px-4 py-3 text-xs"><span className={`px-1.5 py-0.5 rounded text-xs ${wo.source === 'auto' ? 'bg-purple-900 text-purple-300' : 'bg-slate-700 text-slate-300'}`}>{wo.source}</span></td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{new Date(wo.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 flex-wrap">
                        {nextStates.map(ns => (
                          <button
                            key={ns}
                            onClick={() => { setShowTransition(wo); setTransitionNote(''); }}
                            className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded"
                          >
                            {ns === 'acknowledged' ? 'Acknowledge' :
                             ns === 'in_progress' ? 'Start Work' :
                             ns === 'resolved' ? 'Resolve' :
                             ns === 'closed' ? 'Close' :
                             ns === 'rejected' ? 'Reject' : ns}
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

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">Create Work Order</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Edge ID</label>
                <input value={woEdgeId} onChange={e => setWoEdgeId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Equipment ID</label>
                <input value={woEquipId} onChange={e => setWoEquipId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Severity</label>
                <select value={woSeverity} onChange={e => setWoSeverity(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
                  <option value="critical">Critical</option>
                  <option value="warning">Warning</option>
                  <option value="info">Info</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Title</label>
                <input value={woTitle} onChange={e => setWoTitle(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Description</label>
                <textarea value={woDesc} onChange={e => setWoDesc(e.target.value)} rows={3} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
              <button
                onClick={() => createMut.mutate({ edge_id: woEdgeId, equipment_id: woEquipId, severity: woSeverity, title: woTitle, description: woDesc })}
                disabled={createMut.isPending || !woEdgeId || !woEquipId || !woTitle}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {createMut.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
            {createMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(createMut.error as Error).message}</p>
            )}
          </div>
        </div>
      )}

      {showTransition && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-sm">
            <h3 className="text-lg font-bold mb-2">Transition Work Order</h3>
            <p className="text-sm text-slate-400 mb-3">{showTransition.title} — Current: <span className={statusBadge(showTransition.status)}>{showTransition.status}</span></p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Available transitions:</label>
                <div className="flex gap-2 flex-wrap">
                  {(VALID_TRANSITIONS[showTransition.status] || []).map(ns => (
                    <button
                      key={ns}
                      onClick={() => transitionMut.mutate({ woId: showTransition.id, toStatus: ns, note: transitionNote || undefined })}
                      disabled={transitionMut.isPending}
                      className="px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
                    >
                      → {ns}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Note (optional)</label>
                <input value={transitionNote} onChange={e => setTransitionNote(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowTransition(null)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
            </div>
            {transitionMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(transitionMut.error as Error).message}</p>
            )}
          </div>
        </div>
      )}

      {selectedDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-lg max-h-[80vh] overflow-auto">
            <h3 className="text-lg font-bold mb-4">Work Order Detail</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-400">ID</dt><dd className="font-mono">{selectedDetail.id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Title</dt><dd>{selectedDetail.title}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Equipment</dt><dd>{selectedDetail.equipment_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Edge</dt><dd>{selectedDetail.edge_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Severity</dt><dd><span className={severityBadge(selectedDetail.severity)}>{selectedDetail.severity}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Status</dt><dd><span className={statusBadge(selectedDetail.status)}>{selectedDetail.status}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Source</dt><dd>{selectedDetail.source}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Assigned To</dt><dd>{selectedDetail.assigned_to || '--'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Created</dt><dd>{new Date(selectedDetail.created_at).toLocaleString()}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Updated</dt><dd>{new Date(selectedDetail.updated_at).toLocaleString()}</dd></div>
              {selectedDetail.resolved_at && <div className="flex justify-between"><dt className="text-slate-400">Resolved</dt><dd>{new Date(selectedDetail.resolved_at).toLocaleString()}</dd></div>}
            </dl>
            {selectedDetail.description && (
              <div className="mt-4">
                <h4 className="text-xs text-slate-400 mb-1">Description</h4>
                <p className="text-sm text-slate-300 bg-slate-700/50 rounded p-3">{selectedDetail.description}</p>
              </div>
            )}
            <div className="flex justify-end mt-6">
              <button onClick={() => setSelectedDetail(null)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
