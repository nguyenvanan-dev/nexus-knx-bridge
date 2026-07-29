import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = 'http://127.0.0.1:5055';

async function proxyRequest(req, params) {
  const token = (await cookies()).get('knx_token')?.value;
  const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
  const setupToken = req.headers.get('x-setup-token');
  const setupHeaders = setupToken ? { 'X-Setup-Token': setupToken } : {};
  const pathArr = (await params).path || [];
  const targetPath = pathArr.join('/');

  const requestUrl = new URL(req.url);
  const url = `${BACKEND_URL}/api/setup/${targetPath}${requestUrl.search}`;
  const options = {
    method: req.method,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...setupHeaders
    },
    cache: 'no-store'
  };

  if (req.method === 'POST' || req.method === 'PUT') {
    try {
      const body = await req.json();
      options.body = JSON.stringify(body);
    } catch (e) {
      // Body optional
    }
  }

  try {
    const res = await fetch(url, options);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  }
}

export async function GET(req, { params }) {
  return proxyRequest(req, params);
}

export async function POST(req, { params }) {
  return proxyRequest(req, params);
}
