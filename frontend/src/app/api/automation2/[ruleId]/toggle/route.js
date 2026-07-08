const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function PUT(request, { params }) {
  const { ruleId } = params;
  const res = await fetch(`${BACKEND}/automation/rules/v2/${ruleId}/toggle`, { method: 'PUT' });
  return Response.json(await res.json());
}
