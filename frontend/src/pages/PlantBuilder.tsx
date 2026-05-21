import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { usePlantStore } from '../plant/store';
import PlantCanvas from '../plant/PlantCanvas';

export default function PlantBuilder() {
  const { id } = useParams();
  const loadPlantData = usePlantStore(s => s.loadPlantData);
  const plantName = usePlantStore(s => s.plantName);
  const equipmentCount = usePlantStore(s => s.equipment.length);
  const pipeCount = usePlantStore(s => s.pipeSegments.length);
  const [showEquipmentPanel, setShowEquipmentPanel] = useState(false);

  const { data: plant, isLoading } = useQuery({
    queryKey: ['plant', id],
    queryFn: () => fetch(`/api/plants/${id}`).then(r => r.json()),
    enabled: !!id,
  });

  useEffect(() => {
    if (plant && id) {
      loadPlantData(plant);
    }
  }, [plant, id, loadPlantData]);

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 5rem)' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-800 border-b border-slate-700 shrink-0">
        <h2 className="text-lg font-bold text-slate-100">
          {id ? `制冷站: ${plantName || id}` : '制冷站构建'}
        </h2>
        <span className="text-xs text-slate-500">
          {equipmentCount} 设备 | {pipeCount} 管段
        </span>
        <div className="flex-1" />
        <button
          onClick={() => setShowEquipmentPanel(v => !v)}
          className="px-3 py-1.5 bg-cyan-600 text-white rounded text-sm hover:bg-cyan-500"
        >
          添加设备
        </button>
        <button className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded text-sm hover:bg-slate-600">
          校验拓扑
        </button>
        <button className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-500">
          保存
        </button>
      </div>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        {showEquipmentPanel && (
          <div className="w-56 bg-slate-800 border-r border-slate-700 p-3 overflow-y-auto shrink-0">
            <h3 className="text-sm font-semibold text-slate-400 mb-2">设备库</h3>
            <p className="text-xs text-slate-600">从设备管理选择设备</p>
          </div>
        )}
        <div className="flex-1 relative bg-slate-900">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-slate-400">加载制冷站...</div>
          ) : (
            <PlantCanvas />
          )}
        </div>
        <div className="w-64 bg-slate-800 border-l border-slate-700 p-3 overflow-y-auto shrink-0">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">属性</h3>
          <p className="text-xs text-slate-600">选择设备或管段查看属性</p>
        </div>
      </div>

      {/* Pipe table */}
      <div className="h-32 bg-slate-800 border-t border-slate-700 p-3 overflow-y-auto shrink-0">
        <h3 className="text-sm font-semibold text-slate-400 mb-2">管段列表</h3>
        <p className="text-xs text-slate-600">暂无管段</p>
      </div>
    </div>
  );
}
