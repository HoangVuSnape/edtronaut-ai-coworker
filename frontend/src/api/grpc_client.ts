// gRPC Client — Frontend → gRPC Gateway → gRPC Server
// ---
// ALL traffic goes through gRPC:
//   Browser → HTTP/JSON → /rpc/* gateway → gRPC channel → gRPC Server (:50051)
//
// The /rpc/ endpoints are a thin HTTP→gRPC translation layer.
// gRPC is the PRIMARY transport protocol.

import { getAuthHeaders } from './auth';

/* ------------------------------------------------------------------ */
/*  Shared types                                                       */
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
/*  Chat via gRPC streaming                                            */
/* ------------------------------------------------------------------ */

/**
 * Stream a chat message through gRPC.
 *
 * Flow: Browser → POST /rpc/chat/{npcId}/stream → gRPC Gateway
 *       → gRPC ChatService.StreamMessage on port 50051
 *       → streamed response tokens
 */
export async function sendMessageStream(
    req: ChatRequest,
    onChunk: (text: string) => void,
): Promise<void> {
    const doFetch = async () => {
        return fetch(`/rpc/chat/${req.npcId}/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
            },
            body: JSON.stringify({
                sessionId: req.sessionId,
                npcId: req.npcId,
                message: req.message,
            }),
        });
    };

    let res = await doFetch();

    // Retry on 401: re-authenticate and try once more
    if (res.status === 401) {
        const { login } = await import('./auth');
        await login('admin@test.com', 'Admin@123');
        res = await doFetch();
    }

    if (!res.ok) {
        throw new Error(`gRPC stream request failed: ${res.status} ${res.statusText}`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error('Response body is not readable');

    const decoder = new TextDecoder();
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        if (text) {
            onChunk(text);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Unary chat via gRPC                                                */
/* ------------------------------------------------------------------ */

/**
 * Send a chat message through gRPC unary call.
 *
 * Flow: Browser → POST /rpc/chat/{npcId}/send → gRPC Gateway
 *       → gRPC ChatService.SendMessage on port 50051
 */
export async function sendMessageGrpc(req: ChatRequest): Promise<ChatResponse> {
    const res = await fetch(`/rpc/chat/${req.npcId}/send`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
        },
        body: JSON.stringify({
            sessionId: req.sessionId,
            npcId: req.npcId,
            message: req.message,
        }),
    });

    if (!res.ok) {
        throw new Error(`gRPC request failed: ${res.status} ${res.statusText}`);
    }

    return res.json();
}
