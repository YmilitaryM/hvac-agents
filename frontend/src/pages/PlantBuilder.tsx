import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import TopologyCanvas from '../components/TopologyCanvas';

export default function PlantBuilder() {
  const { id } = useParams();

  const { data: templates } = useQuery({
    queryKey: ['plant-templates'],
    queryFn: () => fetch('/api/plants/templates').then(r => r.json()),
  });

  const { data: plant } = useQuery({
    queryKey: ['plant', id],
    queryFn: () => fetch(`/api/plants/${id}`).then(r => r.json()),
    enabled: !!id,
  });

  if (!id) {
    return (
      <div>
        <h2 className="text-xl font-bold mb-4">制冷站构建</h2>
        <div className="grid grid-cols-2 gap-4">
          {(templates?.templates || []).map((t: { id: string; name: string; complexity: string; slot_count: number; description: string }) => (
            <div key={t.id} className="bg-slate-800 p-4 rounded-lg border border-slate-700 cursor-pointer hover:border-cyan-500">
              <h3 className="font-bold text-cyan-400">{t.name}</h3>
              <p className="text-xs text-slate-400 mt-1">复杂度: {t.complexity} | 槽位: {t.slot_count}</p>
              <p className="text-xs text-slate-500 mt-1">{t.description}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">制冷站: {plant?.name || id}</h2>
      <TopologyCanvas plantData={plant} />
    </div>
  );
}
