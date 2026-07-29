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

export async function GET() {
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
    const res = await fetch(`${BACKEND_URL}/api/scenes`, { 
      headers,
      cache: 'no-store' 
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
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
    const action = body.action; // 'create', 'update', 'delete'
    
    let res;
    if (action === 'create') {
      res = await fetch(`${BACKEND_URL}/api/scenes`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body.payload)
      });
    } else if (action === 'update') {
      res = await fetch(`${BACKEND_URL}/api/scenes/${body.scene_id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(body.payload)
      });
    } else if (action === 'delete') {
      res = await fetch(`${BACKEND_URL}/api/scenes/${body.scene_id}`, {
        method: 'DELETE',
        headers
      });
    } else if (action === 'test') {
       // Optional: call the run_scene endpoint if available, or just mock it
       // Currently no test endpoint, we'll implement later or mock
       return NextResponse.json({ ok: true, action: "scene_tested" });
    }
    
    if (!res) throw new Error("Invalid action");
    
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
}
