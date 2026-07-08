import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = 'http://127.0.0.1:5055';

export async function GET() {
    const token = (await cookies()).get('knx_token')?.value;
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
  try {
    const res = await fetch(`${BACKEND_URL}/devices`, { headers: authHeaders,  cache: 'no-store' });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
}

export async function POST(req) {
    const token = (await cookies()).get('knx_token')?.value;
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
  try {
    const body = await req.json();
    const action = body.action; // add, update, disable, delete
    
    const res = await fetch(`${BACKEND_URL}/devices/${action}`, {
      method: 'POST',
      headers: { ...authHeaders,  'Content-Type': 'application/json' },
      body: JSON.stringify(body.payload)
    });
    
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
}
