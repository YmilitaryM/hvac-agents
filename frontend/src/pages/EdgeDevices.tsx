import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import KpiCard from '../components/KpiCard';
import Modal from '../components/Modal';
import { fetchEdges, registerEdge, fetchEdgeConfig, setEdgeConfig, fetchOTATasks, createOTATask, deleteEdge, type EdgeDevice } from '../api/edges';

function statusColor(s: string) {
  if (s === 'online') return 'bg-green-500';
  if (s === 'warning') return 'bg-yellow-500';
  return 'bg-red-500';
}

function statusLabel(s: string) {
  if (s === 'online') return '在线';
  if (s === 'warning') return '告警';
  return '离线';
}

export default function EdgeDevices() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showRegister, setShowRegister] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<EdgeDevice | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [showOTA, setShowOTA] = useState(false);

  const [regId, setRegId] = useState('');
  const [regName, setRegName] = useState('');
  const [regPlantId, setRegPlantId] = useState('');
  const [regMode, setRegMode] = useState('hybrid');
  const [regVersion, setRegVersion] = useState('');
  const [configYaml, setConfigYaml] = useState('');
  const [otaVersion, setOtaVersion] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['edges', { status: statusFilter, search }],
    queryFn: () => fetchEdges({ status: statusFilter || undefined, search: search || undefined }),
    refetchInterval: 10000,
  });

  const edges: EdgeDevice[] = data?.edges || [];
  const online = edges.filter(e => e.status === 'online').length;
  const offline = edges.filter(e => e.status === 'offline').length;
  const warning = edges.filter(e => e.status === 'warning').length;

  const registerMut = useMutation({
    mutationFn: registerEdge,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      setShowRegister(false);
      setRegId(''); setRegName(''); setRegPlantId(''); setRegMode('hybrid'); setRegVersion('');
    },
  });

  const configMut = useMutation({
    mutationFn: ({ edgeId, config }: { edgeId: string; config: Record<string, unknown> }) =>
      setEdgeConfig(edgeId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      setShowConfig(false);
    },
  });

  const otaMut = useMutation({
    mutationFn: ({ edgeId, version }: { edgeId: string; version: string }) =>
      createOTATask(edgeId, { version }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edges'] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteEdge,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['edges'] }),
  });

  const openConfig = async (edge: EdgeDevice) => {
    setSelectedEdge(edge);
    try {
      const cfg = await fetchEdgeConfig(edge.edge_id);
      setConfigYaml(typeof cfg === 'string' ? cfg : JSON.stringify(cfg, null, 2));
    } catch {
      setConfigYaml('# 加载配置失败');
    }
    setShowConfig(true);
  };

  const openOTA = (edge: EdgeDevice) => {
    setSelectedEdge(edge);
    setShowOTA(true);
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">边缘设备</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="在线" value={String(online)} color="text-green-400" />
        <KpiCard label="离线" value={String(offline)} color="text-red-400" />
        <KpiCard label="告警" value={String(warning)} color="text-yellow-400" />
        <KpiCard label="总计" value={String(edges.length)} />
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="搜索边缘ID或制冷站ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-400 flex-1 min-w-[200px]"
        />
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200"
        >
          <option value="">全部状态</option>
          <option value="online">在线</option>
          <option value="warning">告警</option>
          <option value="offline">离线</option>
        </select>
        <button
          onClick={() => setShowRegister(true)}
          className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium"
        >
          注册新设备
        </button>
      </div>

      {/* Desktop table */}
      <div className="hidden md:block bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-left">
              <th className="px-4 py-3">边缘ID</th>
              <th className="px-4 py-3">制冷站</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">最后心跳</th>
              <th className="px-4 py-3">版本</th>
              <th className="px-4 py-3">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">加载中...</td></tr>
            ) : edges.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">未找到设备</td></tr>
            ) : (
              edges.map(e => (
                <tr key={e.edge_id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="px-4 py-3 font-mono text-xs">{e.edge_id}</td>
                  <td className="px-4 py-3">{e.plant_id}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(e.status)} text-white`}>
                      {statusLabel(e.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {e.last_heartbeat ? new Date(e.last_heartbeat).toLocaleString() : '--'}
                  </td>
                  <td className="px-4 py-3 text-xs">{e.version}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <button onClick={() => openConfig(e)} className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">配置</button>
                      <button onClick={() => openOTA(e)} className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">OTA</button>
                      <button onClick={() => { if (confirm('确认删除该设备？')) deleteMut.mutate(e.edge_id); }} className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 text-red-300 rounded">删除</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-2">
        {isLoading ? (
          <div className="text-slate-400 text-center py-8">加载中...</div>
        ) : edges.length === 0 ? (
          <div className="text-slate-500 text-center py-8">未找到设备</div>
        ) : (
          edges.map(e => (
            <div key={e.edge_id} className="bg-slate-800 border border-slate-700 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs text-slate-300">{e.edge_id}</span>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(e.status)} text-white`}>
                  {statusLabel(e.status)}
                </span>
              </div>
              <div className="flex gap-3 text-xs text-slate-400 mb-2">
                <span>制冷站: {e.plant_id}</span>
                <span>v{e.version}</span>
              </div>
              <div className="text-xs text-slate-500 mb-2">
                {e.last_heartbeat ? new Date(e.last_heartbeat).toLocaleString() : '--'}
              </div>
              <div className="flex gap-1">
                <button onClick={() => openConfig(e)} className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">配置</button>
                <button onClick={() => openOTA(e)} className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">OTA</button>
                <button onClick={() => { if (confirm('确认删除该设备？')) deleteMut.mutate(e.edge_id); }} className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 text-red-300 rounded">删除</button>
              </div>
            </div>
          ))
        )}
      </div>

      <Modal open={showRegister} onClose={() => setShowRegister(false)} title="注册新边缘设备" maxWidth="max-w-md">
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">边缘ID</label>
            <input value={regId} onChange={e => setRegId(e.target.value)} placeholder="例如 edge-01" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">名称</label>
            <input value={regName} onChange={e => setRegName(e.target.value)} placeholder="例如 冷水机组边缘1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">制冷站ID</label>
            <input value={regPlantId} onChange={e => setRegPlantId(e.target.value)} placeholder="例如 plant-01" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">模式</label>
            <select value={regMode} onChange={e => setRegMode(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
              <option value="hybrid">混合模式</option>
              <option value="acquisition">采集模式</option>
              <option value="control">控制模式</option>
              <option value="inspection">巡检模式</option>
              <option value="full">全功能模式</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">版本</label>
            <input value={regVersion} onChange={e => setRegVersion(e.target.value)} placeholder="例如 1.0.0" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <button onClick={() => setShowRegister(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">取消</button>
          <button
            onClick={() => registerMut.mutate({ id: regId, name: regName, plant_id: regPlantId, mode: regMode, version: regVersion })}
            disabled={registerMut.isPending || !regId || !regName || !regPlantId || !regVersion}
            className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
          >
            {registerMut.isPending ? '注册中...' : '注册'}
          </button>
        </div>
        {registerMut.isError && (
          <p className="text-red-400 text-xs mt-2">{(registerMut.error as Error).message}</p>
        )}
      </Modal>

      <Modal open={showConfig && !!selectedEdge} onClose={() => setShowConfig(false)} title={`配置: ${selectedEdge?.edge_id}`} maxWidth="max-w-lg">
        <textarea
          value={configYaml}
          onChange={e => setConfigYaml(e.target.value)}
          rows={12}
          className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 font-mono"
        />
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={() => setShowConfig(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">关闭</button>
          <button
            onClick={() => {
              try {
                const parsed = JSON.parse(configYaml);
                configMut.mutate({ edgeId: selectedEdge!.edge_id, config: parsed });
              } catch {
                alert('无效的JSON格式');
              }
            }}
            disabled={configMut.isPending}
            className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
          >
            {configMut.isPending ? '保存中...' : '保存'}
          </button>
        </div>
        {configMut.isError && (
          <p className="text-red-400 text-xs mt-2">{(configMut.error as Error).message}</p>
        )}
      </Modal>

      <Modal open={showOTA && !!selectedEdge} onClose={() => setShowOTA(false)} title={`OTA升级: ${selectedEdge?.edge_id}`}>
        <div>
          <label className="block text-xs text-slate-400 mb-1">目标版本</label>
          <input value={otaVersion} onChange={e => setOtaVersion(e.target.value)} placeholder="例如 1.2.0" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <button onClick={() => setShowOTA(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">取消</button>
          <button
            onClick={() => otaMut.mutate({ edgeId: selectedEdge!.edge_id, version: otaVersion })}
            disabled={otaMut.isPending || !otaVersion}
            className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
          >
            {otaMut.isPending ? '创建中...' : '创建OTA任务'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
