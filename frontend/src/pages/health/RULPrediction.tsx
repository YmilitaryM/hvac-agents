import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../../api/health';

export default function RULPrediction() {
  const { data, isLoading } = useQuery({
    queryKey: ['health-rul', 1],
    queryFn: () => healthApi.getRUL(1),
    refetchInterval: 120000,
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">RUL 预测</h1>
      <div className="space-y-4">
        {data.items.map((item, i) => {
          const days = Math.round(item.predicted_hours / 24);
          const daysLo = Math.round(item.ci_lo / 24);
          const daysHi = Math.round(item.ci_hi / 24);
          const urgency = days < 30 ? 'urgent' : days < 90 ? 'warning' : 'normal';
          const borderColor = urgency === 'urgent' ? 'border-red-500' : urgency === 'warning' ? 'border-yellow-500' : 'border-green-500';
          return (
            <div key={i} className={`bg-white rounded-lg shadow p-4 border-l-4 ${borderColor}`}>
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-semibold">设备 {item.equipment_id} - {item.component}</div>
                  <div className="text-sm text-gray-500">模型: {item.degradation_model}</div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold">{days} <span className="text-base text-gray-500">天</span></div>
                  <div className="text-xs text-gray-400">80%CI: {daysLo}-{daysHi} 天</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
