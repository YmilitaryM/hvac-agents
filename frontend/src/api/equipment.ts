const BASE = '/api';

export async function fetchEquipmentTypes(category?: string) {
  const params = category ? `?category=${category}` : '';
  const r = await fetch(`${BASE}/templates/equipment-types${params}`);
  return r.json();
}

export async function fetchEquipment(plantId?: string) {
  const params = plantId ? `?plant_id=${plantId}` : '';
  const r = await fetch(`${BASE}/equipment/${params}`);
  return r.json();
}

export async function createEquipment(data: { name: string; equipment_type_id: string; design_params?: Record<string, unknown> }) {
  const r = await fetch(`${BASE}/equipment/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function deleteEquipment(id: string) {
  await fetch(`${BASE}/equipment/${id}`, { method: 'DELETE' });
}
