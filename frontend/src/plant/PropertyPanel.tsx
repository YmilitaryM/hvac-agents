import { usePlantStore } from './store';
import { getEquipmentTraits, getDisplayPoints, getControlPoints } from './types';

export function PropertyPanel() {
  const selectedId = usePlantStore(s => s.selectedId);
  const equipment = usePlantStore(s => s.equipment);
  const pipeSegments = usePlantStore(s => s.pipeSegments);
  const setSelection = usePlantStore(s => s.setSelection);

  const selectedEquipment = equipment.find(e => e.id === selectedId);
  const selectedPipe = pipeSegments.find(p => p.id === selectedId);

  if (!selectedId) {
    return (
      <div className="w-64 bg-slate-800 border-l border-slate-700 p-3 overflow-y-auto shrink-0">
        <h3 className="text-sm font-semibold text-slate-400 mb-2">属性</h3>
        <p className="text-xs text-slate-600">选择设备或管段查看属性</p>
      </div>
    );
  }

  if (selectedEquipment) {
    const traits = getEquipmentTraits(selectedEquipment.type_code);
    const displayPoints = getDisplayPoints(selectedEquipment.type_code);
    const controlPoints = getControlPoints(selectedEquipment.type_code);

    return (
      <div className="w-64 bg-slate-800 border-l border-slate-700 overflow-y-auto shrink-0">
        <div className="p-3 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: traits.color }} />
            <h3 className="text-sm font-semibold text-slate-200">{selectedEquipment.name}</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">{traits.label}</p>
        </div>

        {/* Control points */}
        <div className="p-3 border-b border-slate-700">
          <h4 className="text-xs font-semibold text-red-400 mb-2">控制点位</h4>
          {controlPoints.length === 0 ? (
            <p className="text-xs text-slate-600">无</p>
          ) : (
            <div className="space-y-1.5">
              {controlPoints.map(p => (
                <div key={p.code} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400" title={p.code}>{p.name}</span>
                  <span className="text-slate-500">{p.unit}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Display points */}
        <div className="p-3 border-b border-slate-700">
          <h4 className="text-xs font-semibold text-cyan-400 mb-2">显示点位</h4>
          {displayPoints.length === 0 ? (
            <p className="text-xs text-slate-600">无</p>
          ) : (
            <div className="space-y-1.5">
              {displayPoints.map(p => (
                <div key={p.code} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400" title={p.code}>{p.name}</span>
                  <span className="text-slate-500">{p.unit}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Design params */}
        {Object.keys(selectedEquipment.design_params).length > 0 && (
          <div className="p-3">
            <h4 className="text-xs font-semibold text-slate-400 mb-2">设计参数</h4>
            <div className="space-y-1">
              {Object.entries(selectedEquipment.design_params).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">{k}</span>
                  <span className="text-slate-300">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (selectedPipe) {
    const fromEq = equipment.find(e => e.id === selectedPipe.from_equipment_id);
    const toEq = equipment.find(e => e.id === selectedPipe.to_equipment_id);

    return (
      <div className="w-64 bg-slate-800 border-l border-slate-700 overflow-y-auto shrink-0">
        <div className="p-3 border-b border-slate-700">
          <h3 className="text-sm font-semibold text-slate-200">管段</h3>
          <p className="text-xs text-slate-500 mt-1 font-mono">{selectedPipe.id}</p>
        </div>
        <div className="p-3 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">源设备</span>
            <span className="text-slate-300">{fromEq?.name || selectedPipe.from_equipment_id}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">源点位</span>
            <span className="text-cyan-400 font-mono">{selectedPipe.from_point_code}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">目标设备</span>
            <span className="text-slate-300">{toEq?.name || selectedPipe.to_equipment_id}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">目标点位</span>
            <span className="text-cyan-400 font-mono">{selectedPipe.to_point_code}</span>
          </div>
          <hr className="border-slate-700" />
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">管径</span>
            <span className="text-slate-300">DN{selectedPipe.diameter_mm}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">长度</span>
            <span className="text-slate-300">{selectedPipe.length_m}m</span>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
