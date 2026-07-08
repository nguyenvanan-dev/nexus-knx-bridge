const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function PUT(request, { params }) {
  const { planId } = params;
  const body = await request.json();
  const res = await fetch(`${BACKEND}/floorplan/plans/${planId}/devices`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return Response.json(await res.json());
}
