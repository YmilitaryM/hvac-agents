import { usePlantStore } from './store';

export function PipeTable() {
  const pipeSegments = usePlantStore(s => s.pipeSegments);
  const equipment = usePlantStore(s => s.equipment);
  const setSelection = usePlantStore(s => s.setSelection);

  const getEqName = (id: string) => equipment.find(e => e.id === id)?.name || id;

  return (
    <div className="h-40 bg-slate-800 border-t border-slate-700 flex flex-col shrink-0">
      <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-400">管段列表</h3>
        <span className="text-xs text-slate-600">{pipeSegments.length} 条</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {pipeSegments.length === 0 ? (
          <p className="text-xs text-slate-600 p-3">暂无管段 — 在画布上拖拽点位连线</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-700">
                <th className="text-left px-3 py-1.5 font-medium">#</th>
                <th className="text-left px-3 py-1.5 font-medium">源设备</th>
                <th className="text-left px-3 py-1.5 font-medium">源点位</th>
                <th className="text-left px-3 py-1.5 font-medium">目标设备</th>
                <th className="text-left px-3 py-1.5 font-medium">管径</th>
                <th className="text-left px-3 py-1.5 font-medium">长度</th>
              </tr>
            </thead>
            <tbody>
              {pipeSegments.map((ps, i) => (
                <tr
                  key={ps.id}
                  onClick={() => setSelection(ps.id)}
                  className="border-b border-slate-700/50 hover:bg-slate-700/50 cursor-pointer text-slate-300"
                >
                  <td className="px-3 py-1 text-slate-600">{i + 1}</td>
                  <td className="px-3 py-1">{getEqName(ps.from_equipment_id)}</td>
                  <td className="px-3 py-1 text-cyan-400 font-mono">{ps.from_point_code}</td>
                  <td className="px-3 py-1">{getEqName(ps.to_equipment_id)}</td>
                  <td className="px-3 py-1">DN{ps.diameter_mm}</td>
                  <td className="px-3 py-1">{ps.length_m}m</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
