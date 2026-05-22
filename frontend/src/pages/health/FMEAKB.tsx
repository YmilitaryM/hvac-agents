import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { healthApi } from '../../api/health';
import { downloadFile } from '../../api/client';
import type { FMEARecord } from '../../api/health';

export default function FMEAKB() {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<FMEARecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const doSearch = async () => {
    setLoading(true);
    const r = await healthApi.searchFMEA(undefined, undefined, search || undefined);
    setResults(r.items);
    setLoading(false);
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadFile('/api/health/fmea/download', 'FMEA_KB.xlsx');
    } catch (e) {
      alert(t('healthFMEA.downloadFailed') + ': ' + (e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const headers: Record<string, string> = {};
      try {
        const token = localStorage.getItem('auth_token');
        if (token) headers['Authorization'] = `Bearer ${token}`;
      } catch {}
      const resp = await fetch('/api/health/fmea/import', {
        method: 'POST',
        headers,
        body: formData,
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      alert(`${t('healthFMEA.importSuccess')}: ${(data as any).count ?? (data as any).length ?? 0} records`);
      doSearch();
    } catch (e) {
      alert(t('healthFMEA.importFailed') + ': ' + (e as Error).message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('healthFMEA.title')}</h1>
        <div className="flex gap-2">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
          >
            {downloading ? t('common.downloading') : t('healthFMEA.exportExcel')}
          </button>
          <label className={`bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 cursor-pointer ${uploading ? 'opacity-50' : ''}`}>
            {uploading ? t('healthFMEA.importing') : t('healthFMEA.batchImport')}
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2 mb-4">
          <input
            type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder={t('healthFMEA.searchPlaceholder')}
            className="border rounded px-3 py-2 flex-1"
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          />
          <button onClick={doSearch} disabled={loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            {loading ? t('healthFMEA.searching') : t('healthFMEA.search')}
          </button>
        </div>
        <div className="space-y-3">
          {results.map((r) => (
            <div key={r.id} className="border rounded p-3">
              <div className="flex justify-between">
                <div className="font-semibold">{r.failure_mode}</div>
                <div>
                  <span className="text-sm text-gray-500 mr-2">{t('healthFMEA.rpn')}</span>
                  <span className={`font-bold ${r.rpn > 100 ? 'text-red-600' : r.rpn > 50 ? 'text-yellow-600' : 'text-green-600'}`}>{r.rpn}</span>
                </div>
              </div>
              <div className="text-sm text-gray-500">{r.equipment_type} &gt; {r.component}</div>
              <div className="text-sm text-gray-400 mt-1">S={r.severity} O={r.occurrence} D={r.detection}</div>
              {r.mitigation && <div className="text-sm mt-2 bg-blue-50 rounded p-2">{t('healthFMEA.measures')}: {r.mitigation}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
