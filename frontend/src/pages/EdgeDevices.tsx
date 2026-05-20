import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import KpiCard from '../components/KpiCard';
import { fetchEdges, registerEdge, fetchEdgeConfig, setEdgeConfig, fetchOTATasks, createOTATask, deleteEdge, type EdgeDevice } from '../api/edges';

function statusColor(s: string) {
  if (s === 'online') return 'bg-green-500';
  if (s === 'warning') return 'bg-yellow-500';
  return 'bg-red-500';
}

function statusLabel(s: string) {
  if (s === 'online') return 'Online';
  if (s === 'warning') return 'Warning';
  return 'Offline';
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
      setConfigYaml('# Failed to load config');
    }
    setShowConfig(true);
  };

  const openOTA = async (edge: EdgeDevice) => {
    setSelectedEdge(edge);
    setShowOTA(true);
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Edge Devices</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Online" value={String(online)} color="text-green-400" />
        <KpiCard label="Offline" value={String(offline)} color="text-red-400" />
        <KpiCard label="Warning" value={String(warning)} color="text-yellow-400" />
        <KpiCard label="Total" value={String(edges.length)} />
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by Edge ID or Plant ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-400 flex-1 min-w-[200px]"
        />
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200"
        >
          <option value="">All Status</option>
          <option value="online">Online</option>
          <option value="warning">Warning</option>
          <option value="offline">Offline</option>
        </select>
        <button
          onClick={() => setShowRegister(true)}
          className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium"
        >
          Register New
        </button>
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-left">
              <th className="px-4 py-3">Edge ID</th>
              <th className="px-4 py-3">Plant</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last Heartbeat</th>
              <th className="px-4 py-3">Version</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">Loading...</td></tr>
            ) : edges.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">No devices found</td></tr>
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
                      <button onClick={() => openConfig(e)} className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">Config</button>
                      <button onClick={() => openOTA(e)} className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">OTA</button>
                      <button onClick={() => { if (confirm('Delete this device?')) deleteMut.mutate(e.edge_id); }} className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 text-red-300 rounded">Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showRegister && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">Register New Edge Device</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Edge ID</label>
                <input value={regId} onChange={e => setRegId(e.target.value)} placeholder="e.g. edge-01" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Name</label>
                <input value={regName} onChange={e => setRegName(e.target.value)} placeholder="e.g. Chiller Edge 1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Plant ID</label>
                <input value={regPlantId} onChange={e => setRegPlantId(e.target.value)} placeholder="e.g. plant-01" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Mode</label>
                <select value={regMode} onChange={e => setRegMode(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
                  <option value="hybrid">Hybrid</option>
                  <option value="acquisition">Acquisition</option>
                  <option value="control">Control</option>
                  <option value="inspection">Inspection</option>
                  <option value="full">Full</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Version</label>
                <input value={regVersion} onChange={e => setRegVersion(e.target.value)} placeholder="e.g. 1.0.0" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowRegister(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
              <button
                onClick={() => registerMut.mutate({ id: regId, name: regName, plant_id: regPlantId, mode: regMode, version: regVersion })}
                disabled={registerMut.isPending || !regId || !regName || !regPlantId || !regVersion}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {registerMut.isPending ? 'Registering...' : 'Register'}
              </button>
            </div>
            {registerMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(registerMut.error as Error).message}</p>
            )}
          </div>
        </div>
      )}

      {showConfig && selectedEdge && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-lg">
            <h3 className="text-lg font-bold mb-2">Config: {selectedEdge.edge_id}</h3>
            <textarea
              value={configYaml}
              onChange={e => setConfigYaml(e.target.value)}
              rows={12}
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 font-mono"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowConfig(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Close</button>
              <button
                onClick={() => {
                  try {
                    const parsed = JSON.parse(configYaml);
                    configMut.mutate({ edgeId: selectedEdge.edge_id, config: parsed });
                  } catch {
                    alert('Invalid JSON');
                  }
                }}
                disabled={configMut.isPending}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {configMut.isPending ? 'Saving...' : 'Save'}
              </button>
            </div>
            {configMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(configMut.error as Error).message}</p>
            )}
          </div>
        </div>
      )}

      {showOTA && selectedEdge && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">OTA Update: {selectedEdge.edge_id}</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Target Version</label>
                <input value={otaVersion} onChange={e => setOtaVersion(e.target.value)} placeholder="e.g. 1.2.0" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowOTA(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
              <button
                onClick={() => otaMut.mutate({ edgeId: selectedEdge.edge_id, version: otaVersion })}
                disabled={otaMut.isPending || !otaVersion}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {otaMut.isPending ? 'Creating...' : 'Create OTA Task'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
