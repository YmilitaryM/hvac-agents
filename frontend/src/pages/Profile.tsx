import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { fetchAuditLogs } from '../api/audit';

export default function Profile() {
  const { t } = useTranslation();
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

  const NOTIF_LABELS: Record<string, string> = {
    email_alerts: t('profile.emailAlerts'),
    email_reports: t('profile.emailReports'),
    webhook: t('profile.webhook'),
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">{t('profile.title')}</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">{t('profile.personalInfo')}</h3>
          <div className="space-y-3">
            {[
              [t('profile.username'), 'admin'],
              [t('profile.role'), `${t('role.admin')} (ADMIN)`],
              [t('profile.email'), 'admin@hvac.local'],
              [t('profile.registeredAt'), '2025-01-15'],
            ].map(([label, value]) => (
              <div key={label}>
                <div className="text-xs text-slate-400">{label}</div>
                <div className="text-sm mt-0.5">{value}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">{t('profile.changePassword')}</h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-slate-400 block mb-1">{t('profile.currentPassword')}</label>
              <input
                type="password"
                value={pwForm.current}
                onChange={e => setPwForm(f => ({ ...f, current: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-full text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">{t('profile.newPassword')}</label>
              <input
                type="password"
                value={pwForm.newPw}
                onChange={e => setPwForm(f => ({ ...f, newPw: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-full text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">{t('profile.confirmNewPassword')}</label>
              <input
                type="password"
                value={pwForm.confirm}
                onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-full text-sm"
              />
            </div>
            <button className="bg-cyan-600 hover:bg-cyan-500 px-3 py-1.5 rounded text-sm mt-2">
              {t('profile.updatePassword')}
            </button>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">{t('profile.notificationPrefs')}</h3>
          <div className="space-y-3">
            {Object.entries(NOTIF_LABELS).map(([key, label]) => (
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

        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">{t('profile.operationRecords')}</h3>
          {logs.length === 0 ? (
            <div className="text-slate-500 text-sm py-4 text-center">{t('common.noOpRecords')}</div>
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
