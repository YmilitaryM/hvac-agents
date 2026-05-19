import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import KpiCard from '../components/KpiCard';
import { fetchKpi, fetchAlerts } from '../api/monitoring';

const CHART_DATA = [
  { time: '00:00', cop: 4.2, load: 280, power: 230 },
  { time: '02:00', cop: 4.1, load: 240, power: 205 },
  { time: '04:00', cop: 4.0, load: 200, power: 175 },
  { time: '06:00', cop: 4.3, load: 260, power: 210 },
  { time: '08:00', cop: 4.8, load: 350, power: 255 },
  { time: '10:00', cop: 5.0, load: 400, power: 280 },
  { time: '12:00', cop: 4.5, load: 420, power: 325 },
  { time: '14:00', cop: 4.3, load: 410, power: 330 },
  { time: '16:00', cop: 4.3, load: 380, power: 310 },
  { time: '18:00', cop: 4.6, load: 340, power: 255 },
  { time: '20:00', cop: 4.6, load: 310, power: 235 },
  { time: '22:00', cop: 4.4, load: 260, power: 205 },
];

const DEVICE_DATA = [
  { name: 'CH-1 (离心机)', status: '运行', load: '85%', cop: 4.8 },
  { name: 'CH-2 (离心机)', status: '运行', load: '72%', cop: 4.5 },
  { name: 'CT-1 (冷却塔)', status: '运行', fan: '40 Hz', approach: '4.2°C' },
  { name: 'P-CHW-1 (冷冻泵)', status: '运行', freq: '42 Hz', flow: '320 m³/h' },
  { name: 'P-CW-1 (冷却泵)', status: '运行', freq: '38 Hz', flow: '400 m³/h' },
];

export default function Dashboard() {
  const { data: kpi } = useQuery({
    queryKey: ['kpi'],
    queryFn: fetchKpi,
    refetchInterval: 5000,
  });

  const { data: alertData } = useQuery({
    queryKey: ['alerts', {}],
    queryFn: () => fetchAlerts({ acknowledged: false }),
    refetchInterval: 10000,
  });

  const k = kpi?.kpi || {};
  const alerts = alertData?.alerts || [];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">系统总览</h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="系统 COP" value={k.system_cop?.toFixed(2) || '4.45'} color="text-cyan-400" />
        <KpiCard label="冷负荷 (RT)" value={k.total_cooling_load_rt?.toFixed(0) || '320'} />
        <KpiCard label="总功率 (kW)" value={k.total_power_kw?.toFixed(0) || '245'} />
        <KpiCard label="室外湿球温度 (°C)" value={k.outdoor_wb_temp?.toFixed(1) || '26.0'} />
      </div>

      {/* Main Chart: COP / Load / Power */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
        <h3 className="text-sm text-slate-400 uppercase mb-3">COP / 负荷 / 功率 趋势</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={CHART_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
            <YAxis yAxisId="left" stroke="#64748b" fontSize={12} />
            <YAxis yAxisId="right" orientation="right" stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Line yAxisId="left" type="monotone" dataKey="cop" stroke="#38bdf8" strokeWidth={2} dot={false} name="COP" />
            <Line yAxisId="right" type="monotone" dataKey="load" stroke="#a78bfa" strokeWidth={2} dot={false} name="负荷 (RT)" />
            <Line yAxisId="right" type="monotone" dataKey="power" stroke="#f472b6" strokeWidth={2} dot={false} name="功率 (kW)" />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-2 text-xs text-slate-400">
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-cyan-400 inline-block" /> COP</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-400 inline-block" /> 负荷 (RT)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-pink-400 inline-block" /> 功率 (kW)</span>
        </div>
      </div>

      {/* Bottom row: Device Status + Recent Alerts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Equipment Status */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="text-sm text-slate-400 uppercase mb-3">设备状态</h3>
          <div className="space-y-2">
            {DEVICE_DATA.map(d => (
              <div key={d.name} className="flex items-center justify-between bg-slate-700/50 rounded p-3">
                <div>
                  <div className="text-sm font-medium">{d.name}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {Object.entries(d).filter(([k]) => k !== 'name' && k !== 'status').map(([k, v]) => `${k}: ${v}`).join(' | ')}
                  </div>
                </div>
                <span className="w-2 h-2 rounded-full bg-green-400" title={d.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="text-sm text-slate-400 uppercase mb-3">最近告警</h3>
          {alerts.length === 0 ? (
            <div className="text-slate-500 text-sm text-center py-8">无未确认告警</div>
          ) : (
            <div className="space-y-2">
              {alerts.slice(0, 5).map((a: any) => (
                <div key={a.id} className="flex items-center justify-between bg-slate-700/50 rounded p-2 text-sm">
                  <div>
                    <span className={`px-1.5 py-0.5 rounded text-xs mr-2 ${
                      a.severity === 'critical' ? 'bg-red-600' : a.severity === 'warning' ? 'bg-yellow-500 text-black' : 'bg-blue-600'
                    }`}>
                      {a.severity}
                    </span>
                    {a.message || a.rule_name || '告警'}
                  </div>
                  <span className="text-xs text-slate-400">
                    {a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : ''}
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
