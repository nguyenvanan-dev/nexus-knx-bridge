import { cookies } from 'next/headers';

export const dynamic = 'force-dynamic';

export async function GET(req) {
    const response = await fetch('http://127.0.0.1:5055/bus/stream');
    return new Response(response.body, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    });
}
