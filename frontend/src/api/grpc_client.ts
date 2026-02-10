// gRPC-web client kết nối backend
// ---
// This module defines the shared request/response types and the gRPC-web
// transport implementation.  When a real .proto generated client is available,
// replace the body of `sendMessageGrpc` with the generated stub call.

/* ------------------------------------------------------------------ */
/*  Shared types (used by both gRPC and REST clients)                 */
/* ------------------------------------------------------------------ */

export interface ChatRequest {
    sessionId: string;
    npcId: string;
    message: string;
}

export interface ChatResponse {
    npcId: string;
    assistantMessage: string;
    hint?: string;
    safetyFlags?: string[];
}

export interface Message {
    id: string;
    sender: 'user' | 'npc';
    npcId?: 'gucci_ceo' | 'gucci_chro' | 'gucci_eb_ic';
    text: string;
    timestamp: string;
}

/* ------------------------------------------------------------------ */
/*  gRPC-web implementation                                           */
/* ------------------------------------------------------------------ */

/**
 * Send a chat message to the backend via gRPC-web.
 *
 * TODO: Replace with actual grpc-web generated client when proto
 *       definitions are finalised.  Currently falls back to the REST
 *       transport so the UI remains functional during early dev.
 */
export async function sendMessageGrpc(req: ChatRequest): Promise<ChatResponse> {
    // Placeholder – delegates to REST endpoint until gRPC-web proxy is set up.
    const res = await fetch(`/api/npc/${req.npcId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: req.sessionId, message: req.message }),
    });

    if (!res.ok) {
        throw new Error(`Chat request failed: ${res.status} ${res.statusText}`);
    }

    return res.json();
}
