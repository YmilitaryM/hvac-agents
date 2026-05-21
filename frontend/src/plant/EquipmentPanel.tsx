import { useQuery } from '@tanstack/react-query';
import { usePlantStore } from './store';
import { getEquipmentTraits } from './types';
import { computeLayout } from './autoLayout';

interface EquipmentItem {
  id: string;
  name: string;
  type_code: string;
  plant_id: string | null;
  design_params: Record<string, unknown>;
}

export function EquipmentPanel() {
  const addEquipment = usePlantStore(s => s.addEquipment);
  const storeEquipment = usePlantStore(s => s.equipment);
  const existingIds = new Set(storeEquipment.map(e => e.id));

  const { data, isLoading } = useQuery({
    queryKey: ['equipment-library'],
    queryFn: () => fetch('/api/equipment').then(r => r.json()),
  });

  const equipment: EquipmentItem[] = Array.isArray(data) ? data : (data?.equipment ?? []);

  const availableEquipment = equipment.filter(
    e => !existingIds.has(e.id) && !e.plant_id
  );

  const grouped: Record<string, EquipmentItem[]> = {};
  for (const eq of availableEquipment) {
    (grouped[eq.type_code] ??= []).push(eq);
  }

  const handleAdd = (eq: EquipmentItem) => {
    const pos = computeLayout([{ id: eq.id, type_code: eq.type_code }])[0];
    addEquipment({
      id: eq.id,
      name: eq.name,
      type_code: eq.type_code,
      position: pos,
      design_params: eq.design_params,
    });
  };

  return (
    <div className="w-56 bg-slate-800 border-r border-slate-700 flex flex-col shrink-0">
      <div className="p-3 border-b border-slate-700">
        <h3 className="text-sm font-semibold text-slate-400">设备库</h3>
        <p className="text-xs text-slate-600 mt-1">点击设备添加到画布</p>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-3">
        {isLoading ? (
          <p className="text-xs text-slate-500 p-2">加载设备库...</p>
        ) : availableEquipment.length === 0 ? (
          <p className="text-xs text-slate-600 p-2">暂无可选设备</p>
        ) : (
          Object.entries(grouped).map(([typeCode, items]) => {
            const traits = getEquipmentTraits(typeCode);
            return (
              <div key={typeCode}>
                <div className="text-xs text-slate-500 font-semibold mb-1 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: traits.color }} />
                  {traits.label} ({items.length})
                </div>
                {items.map(eq => (
                  <button
                    key={eq.id}
                    onClick={() => handleAdd(eq)}
                    className="w-full text-left px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-700 rounded mb-0.5 truncate"
                  >
                    {eq.name}
                  </button>
                ))}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
