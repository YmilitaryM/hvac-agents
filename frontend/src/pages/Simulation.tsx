import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchKpi, fetchSnapshot } from '../api/monitoring';
import { runSimulation, injectFault, fetchFaults, createWhatIf } from '../api/simulation';
import KpiCard from '../components/KpiCard';

export default function Simulation() {
  const { t } = useTranslation();
  const [plantId, setPlantId] = useState('plant-1');
  const [running, setRunning] = useState(false);
  const [faultForm, setFaultForm] = useState({ device_id: 'CH-1', fault_type: 'fouling', severity: 0.3 });
  const [whatIfScenarios, setWhatIfScenarios] = useState([{ name: 'baseline', offset: 0 }, { name: 'optimized', offset: 1 }]);
  const [whatIfName, setWhatIfName] = useState('');
  const [whatIfOffset, setWhatIfOffset] = useState(0);

  const FAULT_LABELS: Record<string, string> = {
    fouling: t('simulation.fouling'),
    surge: t('simulation.surge'),
    sensor_failure: t('simulation.sensorFailure'),
    refrigerant_leak: t('simulation.refrigerantLeak'),
    valve_sticking: t('simulation.valveSticking'),
  };

  const { data: kpi } = useQuery({ queryKey: ['kpi'], queryFn: fetchKpi, refetchInterval: 5000 });
  const { data: snapshot } = useQuery({ queryKey: ['snapshot'], queryFn: fetchSnapshot, refetchInterval: 10000 });
  const { data: faults } = useQuery({ queryKey: ['faults'], queryFn: fetchFaults, refetchInterval: 10000 });

  const k = kpi?.kpi || {};
  const snap = snapshot || {};
  const copHistory = snap.cop_history || [];

  const handleRun = async () => {
    setRunning(true);
    try {
      await runSimulation({ plant_id: plantId, steps: 24 });
    } finally {
      setRunning(false);
    }
  };

  const handleInjectFault = async () => {
    await injectFault(faultForm);
  };

  const handleAddScenario = () => {
    if (!whatIfName.trim()) return;
    setWhatIfScenarios(s => [...s, { name: whatIfName.trim(), offset: whatIfOffset }]);
    setWhatIfName('');
  };

  const handleRemoveScenario = (idx: number) => {
    setWhatIfScenarios(s => s.filter((_, i) => i !== idx));
  };

  const handleWhatIf = async () => {
    if (whatIfScenarios.length < 2) return;
    const scenarios = whatIfScenarios.map(s => ({
      name: s.name,
      config: { chw_setpoint_offset: s.offset },
    }));
    await createWhatIf({ plant_id: plantId, scenarios });
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">{t('simulation.title')}</h2>

      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4 flex gap-3 items-end flex-wrap">
        <div>
          <label className="text-xs text-slate-400 block mb-1">{t('simulation.plantId')}</label>
          <input
            value={plantId}
            onChange={e => setPlantId(e.target.value)}
            className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-32 text-sm"
          />
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 px-4 py-1.5 rounded text-sm font-medium"
        >
          {running ? t('simulation.running') : t('simulation.runSimulation')}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <KpiCard label={t('simulation.systemCop')} value={k.system_cop?.toFixed(2) || '--'} color="text-cyan-400" />
        <KpiCard label={t('simulation.coolingLoad')} value={k.total_cooling_load_rt?.toFixed(0) || '--'} />
        <KpiCard label={t('simulation.totalPower')} value={k.total_power_kw?.toFixed(0) || '--'} />
        <KpiCard label={t('simulation.outdoorTemp')} value={k.outdoor_wb_temp?.toFixed(1) || '--'} />
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
        <h3 className="text-sm text-slate-400 uppercase mb-3">{t('simulation.copTrend')}</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={copHistory.length > 0 ? copHistory : [
            { time: '00:00', cop: 4.2, load: 280, power: 230 },
            { time: '04:00', cop: 4.0, load: 200, power: 175 },
            { time: '08:00', cop: 4.8, load: 350, power: 255 },
            { time: '12:00', cop: 4.5, load: 420, power: 325 },
            { time: '16:00', cop: 4.3, load: 380, power: 310 },
            { time: '20:00', cop: 4.6, load: 310, power: 235 },
          ]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Line type="monotone" dataKey="cop" stroke="#38bdf8" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="load" stroke="#a78bfa" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="power" stroke="#f472b6" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-2 text-xs text-slate-400">
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-cyan-400 inline-block" /> {t('simulation.cop')}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-400 inline-block" /> {t('simulation.loadRT')}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-pink-400 inline-block" /> {t('simulation.powerKW')}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">{t('simulation.faultInjection')}</h3>
          <div className="space-y-2 mb-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">{t('simulation.deviceId')}</label>
              <input
                value={faultForm.device_id}
                onChange={e => setFaultForm(f => ({ ...f, device_id: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-full text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">{t('simulation.faultType')}</label>
              <select
                value={faultForm.fault_type}
                onChange={e => setFaultForm(f => ({ ...f, fault_type: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-full text-sm"
              >
                {Object.entries(FAULT_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">{t('simulation.severity')}: {faultForm.severity}</label>
              <input
                type="range" min="0" max="1" step="0.05"
                value={faultForm.severity}
                onChange={e => setFaultForm(f => ({ ...f, severity: +e.target.value }))}
                className="w-full"
              />
            </div>
          </div>
          <button onClick={handleInjectFault} className="bg-red-600 hover:bg-red-500 px-3 py-1.5 rounded text-sm">
            {t('simulation.injectFault')}
          </button>
          {faults?.active_faults?.length > 0 && (
            <div className="mt-3 text-sm text-slate-400">
              {t('simulation.activeFaults')}: {faults.active_faults.map((f: any) => f.fault_type).join(', ')}
            </div>
          )}
        </div>

        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="font-medium mb-3">{t('simulation.whatIf')}</h3>
          <div className="space-y-2 mb-3">
            {whatIfScenarios.map((s, i) => (
              <div key={i} className="flex items-center justify-between bg-slate-700 rounded px-3 py-2 text-sm">
                <span>{s.name} <span className="text-slate-400">(offset: {s.offset}&deg;C)</span></span>
                <button onClick={() => handleRemoveScenario(i)} className="text-red-400 hover:text-red-300">&times;</button>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mb-2">
            <input
              value={whatIfName}
              onChange={e => setWhatIfName(e.target.value)}
              placeholder={t('simulation.scenarioName')}
              className="bg-slate-700 border border-slate-600 rounded px-2 py-1 flex-1 text-sm"
            />
            <input
              type="number"
              value={whatIfOffset}
              onChange={e => setWhatIfOffset(+e.target.value)}
              className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-20 text-sm"
              step="0.5"
            />
            <button onClick={handleAddScenario} className="bg-slate-600 hover:bg-slate-500 px-3 py-1 rounded text-sm">
              {t('simulation.addScenario')}
            </button>
          </div>
          <button onClick={handleWhatIf} disabled={whatIfScenarios.length < 2}
            className="bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 px-3 py-1.5 rounded text-sm">
            {t('simulation.submitCompare')} ({whatIfScenarios.length} {t('simulation.scenesCount')})
          </button>
        </div>
      </div>
    </div>
  );
}
