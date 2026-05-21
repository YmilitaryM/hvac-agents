import { useState } from 'react';
import { energyApi } from '../../api/energy';

export default function EnergyScheduling() {
  const [result, setResult] = useState<unknown>(null);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">峰谷负荷调度</h1>
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">分时电价时段</h2>
        <div className="grid grid-cols-3 gap-4 text-center mb-6">
          <div className="bg-green-50 rounded p-3"><div className="text-sm text-gray-500">谷时 (23:00-7:00)</div><div className="text-xl font-bold text-green-600">0.35 元/kWh</div></div>
          <div className="bg-yellow-50 rounded p-3"><div className="text-sm text-gray-500">平时 (7:00-10:00, 15:00-17:00, 21:00-23:00)</div><div className="text-xl font-bold text-yellow-600">0.75 元/kWh</div></div>
          <div className="bg-red-50 rounded p-3"><div className="text-sm text-gray-500">峰时 (10:00-15:00, 17:00-21:00)</div><div className="text-xl font-bold text-red-600">1.15 元/kWh</div></div>
        </div>
        <button
          onClick={async () => { const r = await energyApi.optimizeDemand(1); setResult(r); }}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
        >
          运行优化计算
        </button>
        {result && <pre className="mt-4 p-4 bg-gray-50 rounded text-sm">{JSON.stringify(result, null, 2)}</pre>}
      </div>
    </div>
  );
}
