import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchEquipmentTypes, fetchEquipment, createEquipment, deleteEquipment } from '../api/equipment';
import Modal from '../components/Modal';

export default function Equipment() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTypeId, setNewTypeId] = useState('');

  const { data: typesData } = useQuery({ queryKey: ['equipment-types'], queryFn: () => fetchEquipmentTypes() });
  const { data: eqData } = useQuery({ queryKey: ['equipment'], queryFn: () => fetchEquipment() });

  const createMut = useMutation({
    mutationFn: createEquipment,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['equipment'] }); setShowCreate(false); setNewName(''); setNewTypeId(''); },
  });

  const deleteMut = useMutation({
    mutationFn: deleteEquipment,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['equipment'] }),
  });

  const types = Array.isArray(typesData) ? typesData : [];
  const equipment = Array.isArray(eqData) ? eqData : [];

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">设备管理</h2>
        <button onClick={() => setShowCreate(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm">
          + 添加设备
        </button>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="添加设备">
        <input className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 mb-3 text-sm"
          placeholder="设备名称" value={newName} onChange={e => setNewName(e.target.value)} />
        <select className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 mb-3 text-sm"
          value={newTypeId} onChange={e => setNewTypeId(e.target.value)}>
          <option value="">选择设备类型...</option>
          {types.map((t: { id: string; type_name: string; category: string }) => (
            <option key={t.id} value={t.id}>{t.type_name} ({t.category})</option>
          ))}
        </select>
        <div className="flex gap-2 justify-end">
          <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-slate-400">取消</button>
          <button onClick={() => createMut.mutate({ name: newName, equipment_type_id: newTypeId })}
            className="bg-cyan-600 px-4 py-2 rounded text-sm text-white">创建</button>
        </div>
      </Modal>

      {/* Desktop table */}
      <div className="hidden md:block bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400">
              <th className="text-left p-3">名称</th>
              <th className="text-left p-3">类型</th>
              <th className="text-left p-3">所属制冷站</th>
              <th className="text-left p-3">采集点</th>
              <th className="text-right p-3">操作</th>
            </tr>
          </thead>
          <tbody>
            {equipment.map((eq: { id: string; name: string; equipment_type_id: string; plant_id?: string; points?: Array<unknown> }) => (
              <tr key={eq.id} className="border-b border-slate-700/50">
                <td className="p-3">{eq.name}</td>
                <td className="p-3 text-slate-400">{eq.equipment_type_id}</td>
                <td className="p-3 text-slate-400">{eq.plant_id || '未分配'}</td>
                <td className="p-3 text-slate-400">{eq.points?.length || 0} 个</td>
                <td className="p-3 text-right">
                  <button onClick={() => deleteMut.mutate(eq.id)} className="text-red-400 hover:text-red-300 text-xs">删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-2">
        {equipment.map((eq: { id: string; name: string; equipment_type_id: string; plant_id?: string; points?: Array<unknown> }) => (
          <div key={eq.id} className="bg-slate-800 border border-slate-700 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm">{eq.name}</span>
              <button onClick={() => deleteMut.mutate(eq.id)} className="text-red-400 hover:text-red-300 text-xs">删除</button>
            </div>
            <div className="flex gap-4 text-xs text-slate-400">
              <span>{eq.equipment_type_id}</span>
              <span>{eq.plant_id || '未分配'}</span>
              <span>{eq.points?.length || 0} 个采集点</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
