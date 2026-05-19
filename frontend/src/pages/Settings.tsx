import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchVersions, getVersionDiff } from '../api/versions';

const MOCK_USERS = [
  { id: 'u1', username: 'admin', role: 'ADMIN', email: 'admin@hvac.local', created: '2025-01-15' },
  { id: 'u2', username: 'engineer1', role: 'ENGINEER', email: 'eng1@hvac.local', created: '2025-02-01' },
  { id: 'u3', username: 'operator1', role: 'OPERATOR', email: 'op1@hvac.local', created: '2025-03-10' },
  { id: 'u4', username: 'viewer1', role: 'VIEWER', email: 'viewer@hvac.local', created: '2025-04-20' },
];

const ROLE_LABELS: Record<string, string> = { ADMIN: '管理员', ENGINEER: '工程师', OPERATOR: '操作员', VIEWER: '观察者', AUDITOR: '审计员' };

type Tab = 'users' | 'versions';

export default function Settings() {
  const [tab, setTab] = useState<Tab>('users');
  const [entityType, setEntityType] = useState('plant_topology');
  const [entityId, setEntityId] = useState('plant-1');
  const [diffVer, setDiffVer] = useState<number | null>(null);

  const { data: versions } = useQuery({
    queryKey: ['versions', entityType, entityId],
    queryFn: () => fetchVersions(entityType, entityId),
    enabled: tab === 'versions',
  });

  const { data: diff } = useQuery({
    queryKey: ['diff', entityType, entityId, diffVer],
    queryFn: () => getVersionDiff(entityType, entityId, diffVer!),
    enabled: tab === 'versions' && diffVer !== null,
  });

  const verList = versions?.versions || [];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">系统设置</h2>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setTab('users')}
          className={`px-4 py-1.5 rounded text-sm ${tab === 'users' ? 'bg-cyan-600 text-white' : 'bg-slate-700 text-slate-300'}`}
        >
          用户管理
        </button>
        <button
          onClick={() => setTab('versions')}
          className={`px-4 py-1.5 rounded text-sm ${tab === 'versions' ? 'bg-cyan-600 text-white' : 'bg-slate-700 text-slate-300'}`}
        >
          版本历史
        </button>
      </div>

      {tab === 'users' && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-700">
              <tr>
                <th className="text-left p-3">用户名</th>
                <th className="text-left p-3">角色</th>
                <th className="text-left p-3">邮箱</th>
                <th className="text-left p-3">创建时间</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_USERS.map(u => (
                <tr key={u.id} className="border-t border-slate-700">
                  <td className="p-3">{u.username}</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded text-xs bg-slate-700">{ROLE_LABELS[u.role] || u.role}</span>
                  </td>
                  <td className="p-3 text-slate-400">{u.email}</td>
                  <td className="p-3 text-slate-400">{u.created}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'versions' && (
        <div>
          <div className="flex gap-3 mb-4 items-end">
            <div>
              <label className="text-xs text-slate-400 block mb-1">实体类型</label>
              <select
                value={entityType}
                onChange={e => setEntityType(e.target.value)}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm"
              >
                <option value="plant_topology">制冷站拓扑</option>
                <option value="equipment">设备参数</option>
                <option value="control_strategy">控制策略</option>
                <option value="rl_weights">RL 权重</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">实体 ID</label>
              <input
                value={entityId}
                onChange={e => setEntityId(e.target.value)}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm w-32"
              />
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden mb-4">
            {verList.length === 0 ? (
              <div className="text-slate-500 text-center py-8 text-sm">
                暂无版本记录。修改设备或拓扑后将自动创建版本快照。
              </div>
            ) : (
              verList.map((v: any) => (
                <div
                  key={v.version}
                  className={`flex items-center justify-between p-3 border-b border-slate-700 cursor-pointer hover:bg-slate-700/50 ${
                    diffVer === v.version ? 'bg-slate-700' : ''
                  }`}
                  onClick={() => setDiffVer(diffVer === v.version ? null : v.version)}
                >
                  <div>
                    <span className="font-medium text-sm">v{v.version}</span>
                    <span className="text-xs text-slate-400 ml-3">
                      {new Date(v.created_at).toLocaleString()}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">{v.change_reason || v.changed_by}</span>
                </div>
              ))
            )}
          </div>

          {diff && (
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <h3 className="font-medium mb-2">v{diffVer} 变更对比</h3>
              <pre className="bg-slate-900 rounded p-3 text-xs overflow-auto max-h-64">
                {JSON.stringify(diff.diff || diff, null, 2)}
              </pre>
              {diffVer && (
                <button
                  className="mt-3 bg-yellow-600 hover:bg-yellow-500 px-3 py-1.5 rounded text-sm"
                  onClick={() => alert('回滚功能将调用仿真引擎进行预验证')}
                >
                  回滚到 v{diffVer}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
