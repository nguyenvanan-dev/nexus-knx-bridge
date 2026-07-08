const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const days = searchParams.get('days') || 30;
  const res = await fetch(`${BACKEND}/analytics/summary?days=${days}`);
  return Response.json(await res.json());
}
