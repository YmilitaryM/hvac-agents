import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { usePlantStore } from '../plant/store';
import PlantCanvas from '../plant/PlantCanvas';
import { EquipmentPanel } from '../plant/EquipmentPanel';
import { PropertyPanel } from '../plant/PropertyPanel';
import { PipeTable } from '../plant/PipeTable';
import { validateTopology, type ValidationIssue } from '../plant/validateTopology';

export default function PlantBuilder() {
  const { id } = useParams();
  const loadPlantData = usePlantStore(s => s.loadPlantData);
  const plantName = usePlantStore(s => s.plantName);
  const equipment = usePlantStore(s => s.equipment);
  const pipeSegments = usePlantStore(s => s.pipeSegments);
  const equipmentCount = equipment.length;
  const pipeCount = pipeSegments.length;
  const setSelection = usePlantStore(s => s.setSelection);
  const [showEquipmentPanel, setShowEquipmentPanel] = useState(false);
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[] | null>(null);

  const { data: plant, isLoading, isError } = useQuery({
    queryKey: ['plant', id],
    queryFn: () => fetch(`/api/plants/${id}`).then(r => r.json()),
    enabled: !!id,
  });

  useEffect(() => {
    if (plant && id) {
      loadPlantData(plant);
    }
  }, [plant, id, loadPlantData]);

  const handleValidate = useCallback(() => {
    const issues = validateTopology(equipment, pipeSegments);
    setValidationIssues(issues);
  }, [equipment, pipeSegments]);

  const savePlant = useMutation({
    mutationFn: () => {
      const state = usePlantStore.getState();
      const body = {
        id: state.plantId || undefined,
        name: state.plantName || '新建制冷站',
        equipment: state.equipment.map(e => ({
          id: e.id,
          name: e.name,
          type_code: e.type_code,
          position: e.position,
          design_params: e.design_params,
        })),
        pipe_segments: state.pipeSegments,
      };
      const url = state.plantId ? `/api/plants/${state.plantId}` : '/api/plants/';
      const method = state.plantId ? 'PUT' : 'POST';
      return fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(r => {
        if (!r.ok) throw new Error(`保存失败: ${r.status}`);
        return r.json();
      });
    },
    onSuccess: (data) => {
      usePlantStore.setState({ plantId: data.id, plantName: data.name });
    },
    onError: (err) => {
      console.error('保存失败:', err);
    },
  });

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
        <button
          onClick={handleValidate}
          className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded text-sm hover:bg-slate-600"
        >
          校验拓扑
        </button>
        <button
          onClick={() => savePlant.mutate()}
          disabled={savePlant.isPending}
          className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-500 disabled:opacity-50"
        >
          {savePlant.isPending ? '保存中...' : '保存'}
        </button>
      </div>

      {/* Validation results */}
      {validationIssues !== null && (
        <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 shrink-0">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-slate-400">
              校验结果
              {validationIssues.length === 0
                ? ': 全部正常'
                : `: ${validationIssues.filter(i => i.type === 'error').length} 错误, ${validationIssues.filter(i => i.type === 'warning').length} 警告`}
            </span>
            <button
              onClick={() => setValidationIssues(null)}
              className="text-xs text-slate-500 hover:text-slate-300"
            >
              关闭
            </button>
          </div>
          {validationIssues.length > 0 && (
            <div className="max-h-32 overflow-y-auto space-y-1">
              {validationIssues.map((issue, i) => (
                <div
                  key={i}
                  onClick={() => setSelection(issue.equipmentId || issue.pipeId || null)}
                  className={`text-xs px-2 py-0.5 rounded cursor-pointer ${
                    issue.type === 'error'
                      ? 'bg-red-900/30 text-red-300 hover:bg-red-900/50'
                      : 'bg-yellow-900/30 text-yellow-300 hover:bg-yellow-900/50'
                  }`}
                >
                  <span className="font-semibold">[{issue.tag}]</span> {issue.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        {showEquipmentPanel && <EquipmentPanel />}
        <div className="flex-1 relative bg-slate-900">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-slate-400">加载制冷站...</div>
          ) : isError ? (
            <div className="flex items-center justify-center h-full text-red-400">加载失败，请检查网络连接后刷新页面</div>
          ) : (
            <PlantCanvas />
          )}
        </div>
        <PropertyPanel />
      </div>

      <PipeTable />
    </div>
  );
}
