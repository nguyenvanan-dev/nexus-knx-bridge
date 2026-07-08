const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function GET(request, { params }) {
  const { planId } = params;
  const res = await fetch(`${BACKEND}/floorplan/plans/${planId}`);
  return Response.json(await res.json());
}

export async function DELETE(request, { params }) {
  const { planId } = params;
  const res = await fetch(`${BACKEND}/floorplan/plans/${planId}`, { method: 'DELETE' });
  return Response.json(await res.json());
}
