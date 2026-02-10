// (optional) REST fallback
// ---
// Plain fetch-based client hitting POST /api/npc/{npcId}/chat on the backend.
// This can be used as a simple alternative when gRPC-web is not configured.

import type { ChatRequest, ChatResponse } from './grpc_client';

/**
 * Send a chat message via the REST API.
 */
export async function sendMessageRest(req: ChatRequest): Promise<ChatResponse> {
    const res = await fetch(`/api/npc/${req.npcId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: req.sessionId, message: req.message }),
    });

    if (!res.ok) {
        throw new Error(`REST chat request failed: ${res.status} ${res.statusText}`);
    }

    return res.json();
}
