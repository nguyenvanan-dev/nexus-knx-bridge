import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = 'http://127.0.0.1:5055';
const HEADERS = {
  'Content-Type': 'application/json',
  'X-Knx-Token': 'REMOVED_CREDENTIAL'
};

export async function POST(req) {
    const token = (await cookies()).get('knx_token')?.value;
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
  try {
    const body = await req.json();
    const res = await fetch(`${BACKEND_URL}/api/database/query`, {
      method: 'POST',
      headers: { ...HEADERS, ...authHeaders },
      body: JSON.stringify(body)
    });
    
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
}
