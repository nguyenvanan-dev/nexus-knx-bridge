const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function GET() {
  const res = await fetch(`${BACKEND}/automation/rules/v2`);
  return Response.json(await res.json());
}

export async function POST(request) {
  const body = await request.json();
  const res = await fetch(`${BACKEND}/automation/rules/v2`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return Response.json(await res.json());
}
