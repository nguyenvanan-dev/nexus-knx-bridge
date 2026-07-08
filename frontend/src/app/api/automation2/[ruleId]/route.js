const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function GET(request, { params }) {
  const { ruleId } = params;
  const res = await fetch(`${BACKEND}/automation/rules/v2/${ruleId}`);
  return Response.json(await res.json());
}

export async function PUT(request, { params }) {
  const { ruleId } = params;
  const body = await request.json();
  const res = await fetch(`${BACKEND}/automation/rules/v2/${ruleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return Response.json(await res.json());
}

export async function DELETE(request, { params }) {
  const { ruleId } = params;
  const res = await fetch(`${BACKEND}/automation/rules/v2/${ruleId}`, { method: 'DELETE' });
  return Response.json(await res.json());
}
