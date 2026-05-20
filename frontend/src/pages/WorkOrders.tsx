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

function statusLabel(s: string) {
  const labels: Record<string, string> = {
    open: '待处理',
    acknowledged: '已确认',
    in_progress: '处理中',
    resolved: '已解决',
    closed: '已关闭',
    rejected: '已驳回',
  };
  return labels[s] || s;
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
  const labels: Record<string, string> = {
    critical: '严重',
    warning: '告警',
    info: '信息',
  };
  return labels[s] || s;
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

  const transitionActionLabel = (ns: string) => {
    const labels: Record<string, string> = {
      acknowledged: '确认',
      in_progress: '开始处理',
      resolved: '解决',
      closed: '关闭',
      rejected: '驳回',
    };
    return labels[ns] || ns;
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">工单管理</h2>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <KpiCard label="待处理" value={String(counts.open)} color="text-blue-400" />
        <KpiCard label="已确认" value={String(counts.acknowledged)} color="text-purple-400" />
        <KpiCard label="处理中" value={String(counts.in_progress)} color="text-yellow-400" />
        <KpiCard label="已解决" value={String(counts.resolved)} color="text-green-400" />
        <KpiCard label="已关闭/驳回" value={String(counts.closed_rejected)} color="text-slate-400" />
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="按标题或设备搜索..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-400 flex-1 min-w-[200px]"
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
          <option value="">全部状态</option>
          <option value="open">待处理</option>
          <option value="acknowledged">已确认</option>
          <option value="in_progress">处理中</option>
          <option value="resolved">已解决</option>
          <option value="closed">已关闭</option>
          <option value="rejected">已驳回</option>
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
          <option value="">全部级别</option>
          <option value="critical">严重</option>
          <option value="warning">告警</option>
          <option value="info">信息</option>
        </select>
        <button onClick={() => setShowCreate(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium">
          新建工单
        </button>
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-left">
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">标题</th>
              <th className="px-4 py-3">设备</th>
              <th className="px-4 py-3">级别</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">来源</th>
              <th className="px-4 py-3">创建时间</th>
              <th className="px-4 py-3">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">加载中...</td></tr>
            ) : orders.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">未找到工单</td></tr>
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
                    <td className="px-4 py-3 text-xs"><span className={`px-1.5 py-0.5 rounded text-xs ${wo.source === 'auto' ? 'bg-purple-900 text-purple-300' : 'bg-slate-700 text-slate-300'}`}>{wo.source === 'auto' ? '自动' : '手动'}</span></td>
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

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">新建工单</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">边缘ID</label>
                <input value={woEdgeId} onChange={e => setWoEdgeId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">设备ID</label>
                <input value={woEquipId} onChange={e => setWoEquipId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">级别</label>
                <select value={woSeverity} onChange={e => setWoSeverity(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
                  <option value="critical">严重</option>
                  <option value="warning">告警</option>
                  <option value="info">信息</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">标题</label>
                <input value={woTitle} onChange={e => setWoTitle(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">描述</label>
                <textarea value={woDesc} onChange={e => setWoDesc(e.target.value)} rows={3} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">取消</button>
              <button
                onClick={() => createMut.mutate({ edge_id: woEdgeId, equipment_id: woEquipId, severity: woSeverity, title: woTitle, description: woDesc })}
                disabled={createMut.isPending || !woEdgeId || !woEquipId || !woTitle}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {createMut.isPending ? '创建中...' : '创建'}
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
            <h3 className="text-lg font-bold mb-2">变更工单状态</h3>
            <p className="text-sm text-slate-400 mb-3">{showTransition.title} — 当前: <span className={statusBadge(showTransition.status)}>{statusLabel(showTransition.status)}</span></p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">可执行操作:</label>
                <div className="flex gap-2 flex-wrap">
                  {(VALID_TRANSITIONS[showTransition.status] || []).map(ns => (
                    <button
                      key={ns}
                      onClick={() => transitionMut.mutate({ woId: showTransition.id, toStatus: ns, note: transitionNote || undefined })}
                      disabled={transitionMut.isPending}
                      className="px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
                    >
                      → {transitionActionLabel(ns)}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">备注 (可选)</label>
                <input value={transitionNote} onChange={e => setTransitionNote(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowTransition(null)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">取消</button>
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
            <h3 className="text-lg font-bold mb-4">工单详情</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-400">ID</dt><dd className="font-mono">{selectedDetail.id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">标题</dt><dd>{selectedDetail.title}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">设备</dt><dd>{selectedDetail.equipment_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">边缘</dt><dd>{selectedDetail.edge_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">级别</dt><dd><span className={severityBadge(selectedDetail.severity)}>{severityLabel(selectedDetail.severity)}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">状态</dt><dd><span className={statusBadge(selectedDetail.status)}>{statusLabel(selectedDetail.status)}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">来源</dt><dd>{selectedDetail.source === 'auto' ? '自动' : '手动'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">负责人</dt><dd>{selectedDetail.assigned_to || '--'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">创建时间</dt><dd>{new Date(selectedDetail.created_at).toLocaleString()}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">更新时间</dt><dd>{new Date(selectedDetail.updated_at).toLocaleString()}</dd></div>
              {selectedDetail.resolved_at && <div className="flex justify-between"><dt className="text-slate-400">解决时间</dt><dd>{new Date(selectedDetail.resolved_at).toLocaleString()}</dd></div>}
            </dl>
            {selectedDetail.description && (
              <div className="mt-4">
                <h4 className="text-xs text-slate-400 mb-1">描述</h4>
                <p className="text-sm text-slate-300 bg-slate-700/50 rounded p-3">{selectedDetail.description}</p>
              </div>
            )}
            <div className="flex justify-end mt-6">
              <button onClick={() => setSelectedDetail(null)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
