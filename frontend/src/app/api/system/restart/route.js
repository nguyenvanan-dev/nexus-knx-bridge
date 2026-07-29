import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = 'http://127.0.0.1:5055';
function backendHeaders(authHeaders = {}) {
  const serviceToken = process.env.KNX_API_TOKEN?.trim();
  if (!serviceToken) return null;
  return {
    'Content-Type': 'application/json',
    'X-Knx-Token': serviceToken,
    ...authHeaders
  };
}

export async function POST(req) {
    const token = (await cookies()).get('knx_token')?.value;
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
    const headers = backendHeaders(authHeaders);
    if (!headers) {
      return NextResponse.json(
        { ok: false, error: 'KNX_API_TOKEN is not configured for the frontend service' },
        { status: 503 }
      );
    }
  try {
    const body = await req.json();
    const res = await fetch(`${BACKEND_URL}/api/system/restart`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });
    
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
}
