import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = 'http://127.0.0.1:5055';

export async function GET(req) {
    const token = (await cookies()).get('knx_token')?.value;
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
    const { searchParams } = new URL(req.url);
    const limit = searchParams.get('limit') || '100';

  try {
    const res = await fetch(`${BACKEND_URL}/api/chat-logs?limit=${limit}`, { 
      headers: { 
        'Content-Type': 'application/json',
        ...authHeaders 
      },
      cache: 'no-store' 
    });
    
    if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
}
