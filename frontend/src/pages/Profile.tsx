import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchAuditLogs } from '../api/audit';

export default function Profile() {
  const [pwForm, setPwForm] = useState({ current: '', newPw: '', confirm: '' });
  const [notifications, setNotifications] = useState({
    email_alerts: true,
    email_reports: false,
    webhook: false,
  });

  const { data: auditData } = useQuery({
    queryKey: ['my-audit-log'],
    queryFn: () => fetchAuditLogs({ limit: 20 }),
  });

  const logs = auditData?.logs || [];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">个人设置</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Personal Info */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">个人信息</h3>
          <div className="space-y-3">
            {[
              ['用户名', 'admin'],
              ['角色', '管理员 (ADMIN)'],
              ['邮箱', 'admin@hvac.local'],
              ['注册时间', '2025-01-15'],
            ].map(([label, value]) => (
              <div key={label}>
                <div className="text-xs text-slate-400">{label}</div>
                <div className="text-sm mt-0.5">{value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Password Change */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">修改密码</h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-slate-400 block mb-1">当前密码</label>
              <input
                type="password"
                value={pwForm.current}
                onChange={e => setPwForm(f => ({ ...f, current: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-full text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">新密码</label>
              <input
                type="password"
                value={pwForm.newPw}
                onChange={e => setPwForm(f => ({ ...f, newPw: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-full text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">确认新密码</label>
              <input
                type="password"
                value={pwForm.confirm}
                onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-full text-sm"
              />
            </div>
            <button className="bg-cyan-600 hover:bg-cyan-500 px-3 py-1.5 rounded text-sm mt-2">
              更新密码
            </button>
          </div>
        </div>

        {/* Notification Preferences */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">通知偏好</h3>
          <div className="space-y-3">
            {[
              ['email_alerts', '告警邮件通知'],
              ['email_reports', '日报邮件'],
              ['webhook', 'Webhook 推送'],
            ].map(([key, label]) => (
              <label key={key} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={(notifications as any)[key]}
                  onChange={e => setNotifications(n => ({ ...n, [key]: e.target.checked }))}
                  className="rounded"
                />
                <span className="text-sm">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Personal Audit Log */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">操作记录</h3>
          {logs.length === 0 ? (
            <div className="text-slate-500 text-sm py-4 text-center">暂无操作记录</div>
          ) : (
            <div className="max-h-48 overflow-auto space-y-1">
              {logs.map((log: any) => (
                <div key={log.id} className="text-xs flex justify-between py-1 border-b border-slate-700/50">
                  <span>
                    <span className="text-slate-400">{log.action}</span>
                    <span className="text-slate-500 ml-2">{log.resource_type}</span>
                  </span>
                  <span className="text-slate-500">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
