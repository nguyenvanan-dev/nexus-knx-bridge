// Next.js API routes for floor plan proxying
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function GET() {
  const res = await fetch(`${BACKEND}/floorplan/plans`);
  const data = await res.json();
  return Response.json(data);
}

export async function POST(request) {
  const body = await request.json();
  const res = await fetch(`${BACKEND}/floorplan/plans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return Response.json(await res.json());
}
