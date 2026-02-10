// NPC Toggle Panel
// ---
// Sidebar panel that lets the user enable/disable NPC coworkers and
// switch the active conversation target.

import './NpcTogglePanel.css';

/* ------------------------------------------------------------------ */
/*  NPC descriptors                                                   */
/* ------------------------------------------------------------------ */

interface NpcInfo {
    id: string;
    label: string;
    role: string;
    emoji: string;
}

const NPCS: NpcInfo[] = [
    { id: 'gucci_ceo', label: 'Gucci Group CEO', role: 'Chief Executive Officer', emoji: '👔' },
    { id: 'gucci_chro', label: 'Gucci Group CHRO', role: 'Chief Human Resources Officer', emoji: '🤝' },
    { id: 'gucci_eb_ic', label: 'EB & IC Manager', role: 'Employer Branding & Internal Comms', emoji: '📢' },
];

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface NpcTogglePanelProps {
    enabledNpcIds: string[];
    activeNpcId: string;
    onToggle: (npcId: string) => void;
    onChangeActive: (npcId: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export function NpcTogglePanel({
    enabledNpcIds,
    activeNpcId,
    onToggle,
    onChangeActive,
}: NpcTogglePanelProps) {
    return (
        <nav className="npc-panel" aria-label="AI Coworkers">
            <h2 className="npc-panel-title">AI Coworkers</h2>
            <p className="npc-panel-subtitle">Toggle on / off & select active</p>

            <ul className="npc-list">
                {NPCS.map((npc) => {
                    const enabled = enabledNpcIds.includes(npc.id);
                    const active = npc.id === activeNpcId;

                    return (
                        <li key={npc.id} className={`npc-card ${active ? 'npc-active' : ''} ${!enabled ? 'npc-disabled' : ''}`}>
                            {/* Toggle switch */}
                            <label className="npc-toggle" title={enabled ? 'Disable' : 'Enable'}>
                                <input
                                    type="checkbox"
                                    checked={enabled}
                                    onChange={() => onToggle(npc.id)}
                                    aria-label={`Toggle ${npc.label}`}
                                />
                                <span className="npc-toggle-slider" />
                            </label>

                            {/* Card content – clickable to set active */}
                            <button
                                className="npc-card-body"
                                onClick={() => enabled && onChangeActive(npc.id)}
                                disabled={!enabled}
                                aria-label={`Chat with ${npc.label}`}
                            >
                                <span className="npc-emoji">{npc.emoji}</span>
                                <div className="npc-info">
                                    <span className="npc-name">{npc.label}</span>
                                    <span className="npc-role">{npc.role}</span>
                                </div>
                            </button>
                        </li>
                    );
                })}
            </ul>

            <div className="npc-panel-footer">
                <small>Gucci HRM Simulation</small>
            </div>
        </nav>
    );
}
