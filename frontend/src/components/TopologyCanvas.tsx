import ReactFlow, { Background, Controls } from 'reactflow';
import type { Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';

interface PlantData {
  equipment?: Array<{ id: string; name: string }>;
  pipe_segments?: Array<{ id: string; from_point_id: string; to_point_id: string }>;
}

function buildGraph(plantData: PlantData): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  (plantData.equipment || []).forEach((eq, i) => {
    nodes.push({
      id: eq.id,
      data: { label: eq.name },
      position: { x: 100 + (i % 3) * 200, y: 100 + Math.floor(i / 3) * 120 },
      style: {
        background: '#1e3a5f',
        color: '#93c5fd',
        border: '1px solid #3b82f6',
        borderRadius: 6,
        padding: 8,
        fontSize: 12,
      },
    });
  });

  (plantData.pipe_segments || []).forEach((ps) => {
    edges.push({
      id: ps.id,
      source: ps.from_point_id,
      target: ps.to_point_id,
      animated: true,
      style: { stroke: '#38bdf8' },
    });
  });

  return { nodes, edges };
}

export default function TopologyCanvas({ plantData }: { plantData: PlantData }) {
  const { nodes, edges } = buildGraph(plantData);

  return (
    <div className="h-[500px] bg-slate-900 rounded-lg border border-slate-700">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#334155" />
        <Controls />
      </ReactFlow>
    </div>
  );
}
