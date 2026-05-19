import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

interface WeatherRow {
  hour: number;
  db_temp: number;
  wb_temp: number;
  month: number;
}

function generateTmySample(): WeatherRow[] {
  const rows: WeatherRow[] = [];
  for (let h = 0; h < 168; h++) {
    const month = Math.floor(h / 730) % 12 + 1;
    const tBase = 28 + 8 * Math.sin((2 * Math.PI * (month - 1)) / 12);
    const tDaily = 6 * Math.sin((2 * Math.PI * (h % 24 - 14)) / 24);
    rows.push({
      hour: h,
      db_temp: Math.round((tBase + tDaily) * 10) / 10,
      wb_temp: Math.round((tBase + tDaily - 7) * 10) / 10,
      month,
    });
  }
  return rows;
}

const TMY_SAMPLE = generateTmySample();

export default function Environment() {
  const [tmyView, setTmyView] = useState(false);
  const [priceTab, setPriceTab] = useState<'peak' | 'flat' | 'valley'>('peak');

  const { data: envData } = useQuery({
    queryKey: ['env'],
    queryFn: () => fetch('/api/env').then(r => r.json()),
  });

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">环境配置</h2>

      {/* Weather / TMY Section */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium">气象数据 (TMY)</h3>
          <button
            onClick={() => setTmyView(!tmyView)}
            className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded"
          >
            {tmyView ? '隐藏' : '查看典型年数据'}
          </button>
        </div>
        {tmyView && (
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-slate-400">
                <tr>
                  <th className="text-left py-1">小时</th>
                  <th className="text-left py-1">月</th>
                  <th className="text-left py-1">干球温度 (°C)</th>
                  <th className="text-left py-1">湿球温度 (°C)</th>
                </tr>
              </thead>
              <tbody>
                {TMY_SAMPLE.map(r => (
                  <tr key={r.hour} className="border-t border-slate-700">
                    <td className="py-1">{r.hour}</td>
                    <td className="py-1">{r.month}</td>
                    <td className="py-1">{r.db_temp}</td>
                    <td className="py-1">{r.wb_temp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Electricity Price */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
        <h3 className="font-medium mb-3">电价设置 (元/kWh)</h3>
        <div className="flex gap-2 mb-3">
          {(['peak', 'flat', 'valley'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setPriceTab(tab)}
              className={`px-3 py-1 rounded text-sm ${
                priceTab === tab ? 'bg-cyan-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              {{ peak: '尖峰', flat: '平段', valley: '低谷' }[tab]}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-700 rounded p-3 text-center">
            <div className="text-xs text-slate-400">尖峰 (10:00-12:00, 14:00-17:00)</div>
            <div className="text-lg font-bold text-yellow-400">1.20</div>
          </div>
          <div className="bg-slate-700 rounded p-3 text-center">
            <div className="text-xs text-slate-400">平段 (7:00-10:00, 12:00-14:00, 17:00-22:00)</div>
            <div className="text-lg font-bold text-blue-400">0.75</div>
          </div>
          <div className="bg-slate-700 rounded p-3 text-center">
            <div className="text-xs text-slate-400">低谷 (22:00-7:00)</div>
            <div className="text-lg font-bold text-green-400">0.35</div>
          </div>
        </div>
      </div>

      {/* Building Parameters */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 className="font-medium mb-3">建筑模型参数</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[
            ['建筑面积 (m²)', '50,000'],
            ['窗墙比', '0.35'],
            ['围护结构传热系数 (W/m²·K)', '0.45'],
            ['人员密度 (人/m²)', '0.10'],
            ['照明功率密度 (W/m²)', '9.0'],
            ['设备功率密度 (W/m²)', '15.0'],
            ['新风量 (m³/h·人)', '30'],
            ['室内设计温度 (°C)', '26'],
            ['室内设计湿度 (%)', '55'],
          ].map(([label, value]) => (
            <div key={label} className="bg-slate-700 rounded p-3">
              <div className="text-xs text-slate-400">{label}</div>
              <div className="font-medium mt-1">{value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
