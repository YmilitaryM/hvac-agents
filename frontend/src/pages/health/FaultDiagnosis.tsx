import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { healthApi } from '../../api/health';
import { downloadFile } from '../../api/client';
import type { DiagnosisResult } from '../../api/health';

export default function FaultDiagnosis() {
  const { t } = useTranslation();
  const [equipmentId, setEquipmentId] = useState(1);
  const [results, setResults] = useState<DiagnosisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<unknown>(null);
  const [downloading, setDownloading] = useState(false);

  const runDiagnosis = async () => {
    setLoading(true);
    const r = await healthApi.runDiagnosis(equipmentId);
    setResults(r.diagnoses);
    setLoading(false);
    const h = await healthApi.getDiagnosis(equipmentId);
    setHistory(h);
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadFile(`/api/health/diagnosis/download?equipment_id=${equipmentId}`, `Fault_Diagnosis_${equipmentId}.xlsx`);
    } catch (e) {
      alert(t('healthDiagnosis.downloadFailed') + ': ' + (e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('healthDiagnosis.title')}</h1>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
        >
          {downloading ? t('common.downloading') : t('healthDiagnosis.exportExcel')}
        </button>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4 mb-4">
          <label className="text-sm text-gray-600">{t('healthDiagnosis.deviceId')}:</label>
          <input type="number" value={equipmentId} onChange={(e) => setEquipmentId(Number(e.target.value))}
                 className="border rounded px-3 py-1 w-24" />
          <button onClick={runDiagnosis} disabled={loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
            {loading ? t('healthDiagnosis.diagnosing') : t('healthDiagnosis.runDiagnosis')}
          </button>
        </div>
        {results.length > 0 && (
          <div className="space-y-3">
            {results.map((r, i) => (
              <div key={i} className="border rounded p-3 flex justify-between items-center">
                <div>
                  <div className="font-semibold">#{r.rank}: {r.failure_mode}</div>
                  <div className="text-sm text-gray-500">FMEA #{r.fmea_id} | {t('healthDiagnosis.severity')}: {r.severity}/5</div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-blue-600">{(r.confidence * 100).toFixed(0)}%</div>
                  <div className="text-xs text-gray-400">{t('healthDiagnosis.confidence')}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {history && <pre className="mt-4 p-4 bg-gray-50 rounded text-xs">{JSON.stringify(history, null, 2)}</pre>}
      </div>
    </div>
  );
}
