import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import KpiCard from '../components/KpiCard';
import { evaluateDegradation, predictFailure, type DegradationResult, type PredictResult } from '../api/maintenance';

export default function Maintenance() {
  const { t } = useTranslation();
  const [edgeId, setEdgeId] = useState('');
  const [equipmentId, setEquipmentId] = useState('');
  const [equipmentType, setEquipmentType] = useState('chiller');
  const [designCop, setDesignCop] = useState('5.5');
  const [copWindow, setCopWindow] = useState('5.2,5.1,5.0,4.9,4.8');
  const [approachTempAvg, setApproachTempAvg] = useState('2.5');
  const [vibrationWindow, setVibrationWindow] = useState('1.2,1.3,1.5,1.8,2.1');
  const [evalResult, setEvalResult] = useState<DegradationResult | null>(null);

  const [predCop, setPredCop] = useState('4.5');
  const [predVib, setPredVib] = useState('2.5');
  const [predApproach, setPredApproach] = useState('3.2');
  const [predResult, setPredResult] = useState<PredictResult | null>(null);

  const evalMut = useMutation({
    mutationFn: evaluateDegradation,
    onSuccess: (data) => setEvalResult(data),
  });

  const predMut = useMutation({
    mutationFn: predictFailure,
    onSuccess: (data) => setPredResult(data),
  });

  const severityColor = (s: string) => {
    if (s === 'healthy') return 'bg-green-500';
    if (s === 'degrading') return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const severityLabel = (s: string) => {
    if (s === 'healthy') return t('maintenance.healthy');
    if (s === 'degrading') return t('maintenance.degrading');
    return t('maintenance.critical');
  };

  const probGaugeColor = (p: number) => {
    if (p < 0.3) return 'text-green-400';
    if (p < 0.7) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">{t('maintenance.title')}</h2>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <KpiCard label={t('maintenance.healthy')} value="--" color="text-green-400" />
        <KpiCard label={t('maintenance.degrading')} value="--" color="text-yellow-400" />
        <KpiCard label={t('maintenance.critical')} value="--" color="text-red-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="text-sm text-slate-400 uppercase mb-4">{t('maintenance.degradationEval')}</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('maintenance.equipmentId')}</label>
              <input value={equipmentId} onChange={e => setEquipmentId(e.target.value)} placeholder="e.g. chiller-1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('maintenance.designCop')}</label>
              <input value={designCop} onChange={e => setDesignCop(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('maintenance.copWindow')}</label>
              <input value={copWindow} onChange={e => setCopWindow(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('maintenance.approachTempAvg')}</label>
              <input value={approachTempAvg} onChange={e => setApproachTempAvg(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('maintenance.vibrationWindow')}</label>
              <input value={vibrationWindow} onChange={e => setVibrationWindow(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <button
              onClick={() => evalMut.mutate({
                edge_id: edgeId || 'edge-01',
                equipment_id: equipmentId || 'chiller-1',
                equipment_type: equipmentType,
                design_cop: parseFloat(designCop) || 5.5,
                cop_window: copWindow.split(',').map(Number),
                approach_temp_avg: parseFloat(approachTempAvg) || 2.5,
                vibration_window: vibrationWindow.split(',').map(Number),
              })}
              disabled={evalMut.isPending}
              className="w-full bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
            >
              {evalMut.isPending ? t('maintenance.evaluating') : t('maintenance.runEval')}
            </button>
          </div>

          {evalMut.isError && (
            <p className="text-red-400 text-xs mt-3">{(evalMut.error as Error).message}</p>
          )}

          {evalResult && (
            <div className="mt-4 bg-slate-700/50 rounded p-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${severityColor(evalResult.severity)}`} />
                <span className="font-semibold">{severityLabel(evalResult.severity)}</span>
              </div>
              <div className="text-sm text-slate-300 grid grid-cols-2 gap-2">
                <div>{t('maintenance.copDegradationRate')}: <span className="text-white">{evalResult.cop_degradation_pct.toFixed(1)}%</span></div>
                <div>{t('maintenance.cusumTriggered')}: <span className={evalResult.cusum_triggered ? 'text-red-400' : 'text-green-400'}>{evalResult.cusum_triggered ? t('maintenance.yes') : t('maintenance.no')}</span></div>
              </div>
              {evalResult.recommended_action && (
                <div className="text-sm bg-slate-800 rounded p-2 text-slate-300">{evalResult.recommended_action}</div>
              )}
            </div>
          )}
        </div>

        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="text-sm text-slate-400 uppercase mb-4">{t('maintenance.failurePrediction')}</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('maintenance.currentCop')}</label>
              <input value={predCop} onChange={e => setPredCop(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('maintenance.vibrationRMS')}</label>
              <input value={predVib} onChange={e => setPredVib(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('maintenance.approachTemp')}</label>
              <input value={predApproach} onChange={e => setPredApproach(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <button
              onClick={() => predMut.mutate({
                cop_current: parseFloat(predCop) || 4.5,
                vibration_rms: parseFloat(predVib) || 2.5,
                approach_temp: parseFloat(predApproach) || 3.2,
              })}
              disabled={predMut.isPending}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
            >
              {predMut.isPending ? t('maintenance.predicting') : t('maintenance.predictFailure')}
            </button>
          </div>

          {predMut.isError && (
            <p className="text-red-400 text-xs mt-3">{(predMut.error as Error).message}</p>
          )}

          {predResult && (
            <div className="mt-4 bg-slate-700/50 rounded p-4 flex flex-col items-center">
              <div className="text-xs text-slate-400 mb-2">{t('maintenance.failureProb')}</div>
              <div className={`text-5xl font-bold ${probGaugeColor(predResult.failure_probability)}`}>
                {(predResult.failure_probability * 100).toFixed(1)}%
              </div>
              <div className="w-full bg-slate-800 rounded-full h-3 mt-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${predResult.failure_probability < 0.3 ? 'bg-green-500' : predResult.failure_probability < 0.7 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${predResult.failure_probability * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
