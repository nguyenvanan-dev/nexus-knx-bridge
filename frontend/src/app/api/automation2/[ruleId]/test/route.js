const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function POST(request, { params }) {
  const { ruleId } = params;
  const res = await fetch(`${BACKEND}/automation/rules/v2/${ruleId}/test`, { method: 'POST' });
  const text = await res.text();
  try { return Response.json(JSON.parse(text), { status: res.status }); }
  catch { return Response.json({ error: text }, { status: res.status }); }
}
