import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';

export default function EnergyMV() {
  const { data, isLoading } = useQuery({
    queryKey: ['energy-mv', 1],
    queryFn: () => energyApi.getMv(1),
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">M&V 验证</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">节能量</div>
          <div className="text-2xl font-bold text-green-600">{data.savings_kwh.toLocaleString()} kWh</div>
          <div className="text-sm text-gray-400">{data.savings_pct}%</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">标准煤节约</div>
          <div className="text-2xl font-bold">{data.coal_equivalent_tons} 吨</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">碳减排</div>
          <div className="text-2xl font-bold text-cyan-600">{data.carbon_reduction_kg.toLocaleString()} kg</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">CV(RMSE)</div>
          <div className={`text-2xl font-bold ${data.cv_rmse_pct <= 20 ? 'text-green-600' : 'text-red-600'}`}>{data.cv_rmse_pct}%</div>
          <div className="text-sm text-gray-400">{data.cv_rmse_pct <= 20 ? 'ASHRAE G14 合规' : '超标'}</div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">国标合规</h2>
          <div className="space-y-2">
            <div className={`flex items-center gap-2 ${data.compliant_gb28750 ? 'text-green-600' : 'text-red-600'}`}>
              {data.compliant_gb28750 ? '✓' : '✗'} GB/T 28750 M&V 验证通过
            </div>
            <div className={`flex items-center gap-2 ${data.compliant_ashrae_g14 ? 'text-green-600' : 'text-red-600'}`}>
              {data.compliant_ashrae_g14 ? '✓' : '✗'} ASHRAE Guideline 14 合规
            </div>
            <div className={`flex items-center gap-2 ${Math.abs(data.nmbe_pct) <= 5 ? 'text-green-600' : 'text-red-600'}`}>
              {Math.abs(data.nmbe_pct) <= 5 ? '✓' : '✗'} NMBE: {data.nmbe_pct}% (≤±5%)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
