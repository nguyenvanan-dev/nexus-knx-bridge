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

        let data;
        const text = await res.text();
        try {
            data = JSON.parse(text);
        } catch (e) {
            return NextResponse.json({
                status: 'error',
                message: `Failed to parse backend response: ${text.slice(0, 100)}`
            }, { status: 502 });
        }

        if (!res.ok) {
            return NextResponse.json({
                status: 'error',
                message: data.message || data.error || `Backend error: HTTP ${res.status}`
            }, { status: res.status });
        }

        return NextResponse.json(data, { status: res.status });
    } catch (error) {
        return NextResponse.json({ status: 'error', message: error.message }, { status: 500 });
    }
}
