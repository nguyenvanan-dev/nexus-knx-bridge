import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = 'http://127.0.0.1:5055';
const HEADERS = {
  'Content-Type': 'application/json',
  'X-Knx-Token': 'REMOVED_CREDENTIAL'
};

export async function GET(req) {
    const token = (await cookies()).get('knx_token')?.value;
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
  try {
    const { searchParams } = new URL(req.url);
    const service = searchParams.get('service') || 'knx-bridge';
    const lines = searchParams.get('lines') || '50';
    
    const res = await fetch(`${BACKEND_URL}/api/system/logs?service=${service}&lines=${lines}`, { 
      headers: HEADERS,
      cache: 'no-store' 
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
}
