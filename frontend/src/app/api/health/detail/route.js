const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5055';

export async function GET() {
  const res = await fetch(`${BACKEND}/health/detail`);
  return Response.json(await res.json());
}
