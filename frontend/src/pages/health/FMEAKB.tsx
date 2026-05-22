import { useState, useRef } from 'react';
import { healthApi } from '../../api/health';
import { downloadFile } from '../../api/client';
import type { FMEARecord } from '../../api/health';

export default function FMEAKB() {
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
      await downloadFile('/api/health/fmea/download', 'FMEA知识库.xlsx');
    } catch (e) {
      alert('下载失败: ' + (e as Error).message);
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
      alert(`导入成功: ${(data as any).count ?? (data as any).length ?? 0} 条记录`);
      doSearch();
    } catch (e) {
      alert('导入失败: ' + (e as Error).message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">FMEA 知识库</h1>
        <div className="flex gap-2">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
          >
            {downloading ? '下载中...' : '导出Excel'}
          </button>
          <label className={`bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 cursor-pointer ${uploading ? 'opacity-50' : ''}`}>
            {uploading ? '导入中...' : '批量导入'}
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
            placeholder="搜索失效模式、部件..."
            className="border rounded px-3 py-2 flex-1"
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          />
          <button onClick={doSearch} disabled={loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>
        <div className="space-y-3">
          {results.map((r) => (
            <div key={r.id} className="border rounded p-3">
              <div className="flex justify-between">
                <div className="font-semibold">{r.failure_mode}</div>
                <div>
                  <span className="text-sm text-gray-500 mr-2">RPN</span>
                  <span className={`font-bold ${r.rpn > 100 ? 'text-red-600' : r.rpn > 50 ? 'text-yellow-600' : 'text-green-600'}`}>{r.rpn}</span>
                </div>
              </div>
              <div className="text-sm text-gray-500">{r.equipment_type} &gt; {r.component}</div>
              <div className="text-sm text-gray-400 mt-1">S={r.severity} O={r.occurrence} D={r.detection}</div>
              {r.mitigation && <div className="text-sm mt-2 bg-blue-50 rounded p-2">措施: {r.mitigation}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
