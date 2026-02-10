// Simulation Layout
// ---
// Top-level layout component.  Owns all session-level state (sessionId,
// messages, NPC selection, hints) and wires the child components together.

import { useState, useCallback } from 'react';
import { ChatWindow } from './ChatWindow';
import { NpcTogglePanel } from './NpcTogglePanel';
import { HintBanner } from './HintBanner';
import { sendMessageGrpc } from '../api/grpc_client';
import type { Message } from '../api/grpc_client';
import './SimulationLayout.css';

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export function SimulationLayout() {
    /* ---------- state ---------- */
    const [sessionId] = useState(() => crypto.randomUUID());

    const [messages, setMessages] = useState<Message[]>([]);

    const [enabledNpcIds, setEnabledNpcIds] = useState<string[]>([
        'gucci_ceo',
        'gucci_chro',
        'gucci_eb_ic',
    ]);

    const [activeNpcId, setActiveNpcId] = useState('gucci_chro');
    const [hint, setHint] = useState<string | undefined>(undefined);
    const [isLoading, setIsLoading] = useState(false);
    const [safetyMessage, setSafetyMessage] = useState<string | undefined>(undefined);

    /* ---------- handlers ---------- */

    const handleToggle = useCallback(
        (npcId: string) => {
            setEnabledNpcIds((prev) => {
                const next = prev.includes(npcId)
                    ? prev.filter((id) => id !== npcId)
                    : [...prev, npcId];

                // If the active NPC was just disabled, switch to first enabled
                if (npcId === activeNpcId && next.length > 0 && !next.includes(activeNpcId)) {
                    setActiveNpcId(next[0]);
                }
                return next;
            });
        },
        [activeNpcId],
    );

    const handleChangeActive = useCallback((npcId: string) => {
        setActiveNpcId(npcId);
    }, []);

    const handleSend = useCallback(
        async (text: string) => {
            // Append user message immediately
            const userMsg: Message = {
                id: crypto.randomUUID(),
                sender: 'user',
                text,
                timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, userMsg]);
            setSafetyMessage(undefined);
            setIsLoading(true);

            try {
                const res = await sendMessageGrpc({
                    sessionId,
                    npcId: activeNpcId,
                    message: text,
                });

                const npcMsg: Message = {
                    id: crypto.randomUUID(),
                    sender: 'npc',
                    npcId: res.npcId as Message['npcId'],
                    text: res.assistantMessage,
                    timestamp: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, npcMsg]);
                setHint(res.hint);

                // Handle safety flags
                if (res.safetyFlags && res.safetyFlags.length > 0) {
                    setSafetyMessage(
                        'This simulation focuses on HRM & leadership at Gucci. Please keep the conversation within this scope.',
                    );
                }
            } catch (err) {
                console.error('Chat error:', err);
                const errorMsg: Message = {
                    id: crypto.randomUUID(),
                    sender: 'npc',
                    npcId: activeNpcId as Message['npcId'],
                    text: 'Sorry, something went wrong. Please try again.',
                    timestamp: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, errorMsg]);
            } finally {
                setIsLoading(false);
            }
        },
        [sessionId, activeNpcId],
    );

    /* ---------- render ---------- */

    return (
        <div className="simulation-layout">
            <aside className="simulation-sidebar">
                <NpcTogglePanel
                    enabledNpcIds={enabledNpcIds}
                    activeNpcId={activeNpcId}
                    onToggle={handleToggle}
                    onChangeActive={handleChangeActive}
                />
            </aside>

            <main className="simulation-main">
                <HintBanner hint={hint} onDismiss={() => setHint(undefined)} />

                {safetyMessage && (
                    <div className="safety-banner" role="alert">
                        <span className="safety-icon">⚠️</span>
                        <p>{safetyMessage}</p>
                        <button onClick={() => setSafetyMessage(undefined)} aria-label="Dismiss">✕</button>
                    </div>
                )}

                <ChatWindow
                    messages={messages}
                    activeNpcId={activeNpcId}
                    onSend={handleSend}
                    isLoading={isLoading}
                />
            </main>
        </div>
    );
}
