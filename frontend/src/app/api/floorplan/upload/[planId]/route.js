const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function POST(request, { params }) {
  const { planId } = params;
  const formData = await request.formData();
  const res = await fetch(`${BACKEND}/floorplan/upload/${planId}`, {
    method: 'POST',
    body: formData,
  });
  return Response.json(await res.json());
}
