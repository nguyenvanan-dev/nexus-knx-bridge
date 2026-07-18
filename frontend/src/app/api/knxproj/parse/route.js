import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:5055';

export async function POST(req) {
    const token = (await cookies()).get('knx_token')?.value;
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
    try {
        const formData = await req.formData();
        const res = await fetch(`${BACKEND_URL}/api/knxproj/parse`, {
            method: 'POST',
            headers: authHeaders,
            body: formData
        });
        const data = await res.json();
        return NextResponse.json(data, { status: res.status });
    } catch (error) {
        return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
    }
}
