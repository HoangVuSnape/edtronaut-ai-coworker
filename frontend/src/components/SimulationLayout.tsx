// Simulation Layout
// ---
// Top-level layout component.  Owns all session-level state (sessionId,
// messages, NPC selection, hints) and wires the child components together.

import { useState, useCallback } from 'react';
import { ChatWindow } from './ChatWindow';
import { NpcTogglePanel } from './NpcTogglePanel';
import { HintBanner } from './HintBanner';
import { sendMessageStream } from '../api/grpc_client';
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

            // Prepare a placeholder NPC message
            const npcId = crypto.randomUUID();
            const npcMsgPlaceholder: Message = {
                id: npcId,
                sender: 'npc',
                npcId: activeNpcId as Message['npcId'],
                text: '',
                timestamp: new Date().toISOString(),
            };

            setMessages((prev) => [...prev, npcMsgPlaceholder]);

            try {
                let fullText = '';
                await sendMessageStream(
                    {
                        sessionId,
                        npcId: activeNpcId,
                        message: text,
                    },
                    (chunk) => {
                        fullText += chunk;
                        const updatedText = fullText;
                        setMessages((prev) =>
                            prev.map((msg) =>
                                msg.id === npcId ? { ...msg, text: updatedText } : msg
                            )
                        );
                    },
                );


                // If we want additional metadata like hints or safety flags,
                // we might need a separate call or a more complex stream protocol (JSON per line).
                // For now, simple text streaming satisfies "hiển thị từ từ".

            } catch (err) {
                console.error('Chat error:', err);
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === npcId
                            ? { ...msg, text: 'Sorry, something went wrong. Please try again.' }
                            : msg
                    )
                );
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
