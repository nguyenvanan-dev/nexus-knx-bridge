import { cookies } from 'next/headers';

export const dynamic = 'force-dynamic';

export async function GET(req) {
    // In a real app we might pass knx_token to Backend, but the backend SSE endpoint currently doesn't check auth for simplicity, or we can add it later.
    const response = await fetch('http://127.0.0.1:5055/events/stream');
    return new Response(response.body, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    });
}
