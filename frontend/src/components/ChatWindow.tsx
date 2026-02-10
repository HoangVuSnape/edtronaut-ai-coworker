// Chat Interface
// ---
// Renders the full conversation history and a message input box.
// Distinguishes user messages from NPC messages, with per-NPC styling.

import { useState, useRef, useEffect } from 'react';
import type { Message } from '../api/grpc_client';
import './ChatWindow.css';

/* ------------------------------------------------------------------ */
/*  NPC display metadata                                              */
/* ------------------------------------------------------------------ */

const NPC_META: Record<string, { label: string; colorClass: string }> = {
    gucci_ceo: { label: 'Gucci Group CEO', colorClass: 'npc-ceo' },
    gucci_chro: { label: 'Gucci Group CHRO', colorClass: 'npc-chro' },
    gucci_eb_ic: { label: 'Employer Branding & IC Manager', colorClass: 'npc-ebic' },
};

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface ChatWindowProps {
    messages: Message[];
    activeNpcId: string;
    onSend: (text: string) => void;
    isLoading?: boolean;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export function ChatWindow({ messages, activeNpcId, onSend, isLoading = false }: ChatWindowProps) {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to latest message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const text = input.trim();
        if (!text || isLoading) return;
        onSend(text);
        setInput('');
    };

    const npcLabel = NPC_META[activeNpcId]?.label ?? activeNpcId;

    return (
        <div className="chat-window">
            {/* ---- Header ---- */}
            <header className="chat-header">
                <div className="chat-header-dot" />
                <span className="chat-header-title">
                    Conversation with <strong>{npcLabel}</strong>
                </span>
            </header>

            {/* ---- Messages ---- */}
            <div className="chat-messages">
                {messages.length === 0 && (
                    <div className="chat-empty">
                        <p className="chat-empty-icon">💬</p>
                        <p>Start the conversation by typing a message below.</p>
                    </div>
                )}

                {messages.map((msg) => {
                    const isUser = msg.sender === 'user';
                    const meta = msg.npcId ? NPC_META[msg.npcId] : undefined;
                    return (
                        <div
                            key={msg.id}
                            className={`chat-bubble ${isUser ? 'bubble-user' : 'bubble-npc'} ${meta?.colorClass ?? ''}`}
                        >
                            <div className="bubble-sender">
                                {isUser ? 'You' : meta?.label ?? 'NPC'}
                            </div>
                            <div className="bubble-text">{msg.text}</div>
                            <time className="bubble-time">
                                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </time>
                        </div>
                    );
                })}

                {isLoading && (
                    <div className="chat-bubble bubble-npc typing-indicator">
                        <span /><span /><span />
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* ---- Input ---- */}
            <form className="chat-input-bar" onSubmit={handleSubmit}>
                <input
                    className="chat-input"
                    type="text"
                    placeholder="Type your message…"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isLoading}
                    autoFocus
                />
                <button
                    className="chat-send-btn"
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    aria-label="Send message"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13" />
                        <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                </button>
            </form>
        </div>
    );
}
