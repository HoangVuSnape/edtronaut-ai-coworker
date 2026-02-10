Dưới đây là file Markdown thuần kỹ thuật, viết như một dev lead mô tả frontend. Bạn có thể lưu thành `frontend/README.md` hoặc `docs/FRONTEND.md`.

```markdown
# Frontend – AI Co‑worker Simulation

This frontend implements the UI layer for the **Edtronaut AI Co‑worker Engine**.  
It provides a simulation environment where learners chat with multiple AI co‑workers (CEO, CHRO, Employer Branding & IC) and receive subtle guidance from a Director agent. [file:16]

---

## 1. Project Structure

```text
frontend/
├── package.json
├── src/
│   ├── App.tsx                  # Root component, wires layout + providers
│   ├── api/
│   │   ├── grpc_client.ts       # gRPC(-web) client to backend chat service
│   │   └── rest_client.ts       # REST fallback client (for local/dev)
│   ├── components/
│   │   ├── ChatWindow.tsx       # Conversation UI (history + input box)
│   │   ├── NpcTogglePanel.tsx   # Toggle + select active NPC (CEO/CHRO/EB&IC)
│   │   ├── HintBanner.tsx       # Displays Director hints when user is stuck
│   │   └── SimulationLayout.tsx # High-level layout combining all widgets
│   └── styles/                  # Global styles / Tailwind config / CSS modules
└── public/
    └── index.html
```

Design goals:

- Single‑page chat experience tailored to the Gucci HRM simulation, not a generic chatbot UI. [file:16]  
- Clear separation between **transport layer** (`api/`) and **presentation components** (`components/`).  
- Minimal but explicit structure so reviewers can understand the flow in seconds.

---

## 2. Data Flow

### 2.1. Session & NPC selection

- Each browser tab holds a `sessionId` (generated client‑side or returned by backend on first call).  
- `NpcTogglePanel` manages:
  - `enabledNpcIds: string[]`
  - `activeNpcId: "gucci_ceo" | "gucci_chro" | "gucci_eb_ic"`  

Flow on user send:

1. User types message in `ChatWindow` and hits “Send”.
2. `ChatWindow` calls `onSend(text)` passed from `SimulationLayout`.
3. `SimulationLayout` calls `api.sendMessage({ sessionId, npcId: activeNpcId, text })`.
4. Backend returns:
   - `assistantMessage`
   - `npcId` (who responded)
   - `hint` (optional, from Director)
   - `safetyFlags` (optional; jailbreak/off‑topic/etc.).
5. State is updated:
   - New `Message` appended to `messages`.
   - `hint` stored and passed into `HintBanner`.

### 2.2. API Layer

`src/api/grpc_client.ts`:

- Exposes a minimal interface:

```ts
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

export async function sendMessageGrpc(req: ChatRequest): Promise<ChatResponse> {
  // gRPC-web implementation goes here
}
```

`src/api/rest_client.ts`:

- Fallback implementation hitting `POST /npc/{npcId}/chat` on the backend.

```ts
export async function sendMessageRest(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`/api/npc/${req.npcId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId: req.sessionId, message: req.message }),
  });
  return res.json();
}
```

A simple configuration flag in `App.tsx` can switch between gRPC and REST clients.

---

## 3. Core Components

### 3.1. SimulationLayout

Top‑level layout component. Responsible for:

- Owning session‑level state: `sessionId`, `messages`, `enabledNpcIds`, `activeNpcId`, `hint`.  
- Passing callbacks and props down to children.

```tsx
// src/components/SimulationLayout.tsx
import { useState } from 'react';
import { ChatWindow } from './ChatWindow';
import { NpcTogglePanel } from './NpcTogglePanel';
import { HintBanner } from './HintBanner';
import { sendMessageGrpc } from '../api/grpc_client';

export function SimulationLayout() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<Message[]>([]);
  const [enabledNpcIds, setEnabledNpcIds] = useState<string[]>([
    'gucci_ceo',
    'gucci_chro',
    'gucci_eb_ic',
  ]);
  const [activeNpcId, setActiveNpcId] = useState('gucci_chro');
  const [hint, setHint] = useState<string | undefined>(undefined);

  const handleSend = async (text: string) => {
    const userMsg: Message = {
      id: crypto.randomUUID(),
      sender: 'user',
      text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    const res = await sendMessageGrpc({ sessionId, npcId: activeNpcId, message: text });

    const npcMsg: Message = {
      id: crypto.randomUUID(),
      sender: 'npc',
      npcId: res.npcId,
      text: res.assistantMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, npcMsg]);
    setHint(res.hint);
  };

  return (
    <div className="simulation-layout">
      <aside className="simulation-sidebar">
        <NpcTogglePanel
          enabledNpcIds={enabledNpcIds}
          activeNpcId={activeNpcId}
          onToggle={/* update enabledNpcIds */}
          onChangeActive={setActiveNpcId}
        />
      </aside>
      <main className="simulation-main">
        <HintBanner hint={hint} />
        <ChatWindow
          messages={messages}
          activeNpcId={activeNpcId}
          onSend={handleSend}
        />
      </main>
    </div>
  );
}
```

### 3.2. ChatWindow

- Renders full conversation history.
- Distinguishes:
  - user vs npc
  - within npc: CEO vs CHRO vs EB&IC (different labels/colors).

```tsx
interface Message {
  id: string;
  sender: 'user' | 'npc';
  npcId?: 'gucci_ceo' | 'gucci_chro' | 'gucci_eb_ic';
  text: string;
  timestamp: string;
}

interface ChatWindowProps {
  messages: Message[];
  activeNpcId: string;
  onSend: (text: string) => void;
}
```

### 3.3. NpcTogglePanel

Encodes the “AI coworkers (toggle on/off)” requirement from the assignment. [file:16]

- If an NPC is disabled, it does not appear as an option for `activeNpcId`.  
- Good UX: CHRO can be default active for the Gucci HRM simulation.

### 3.4. HintBanner

Visualizes the Director layer without breaking immersion:

- Only visible when a non‑empty `hint` is present.  
- Text is neutral and coaching‑style (no wagering language, consistent with safety guardrails). [file:16]

---

## 4. Styling & UX Guidelines

- Layout: chat should feel like a workspace tool, not a gaming UI.
  - Left: NPC list / toggles.
  - Center: conversation.
  - Top of chat: `HintBanner`.
- Accessibility:
  - Clear labels for each NPC: “Gucci Group CEO”, “Gucci Group CHRO”, “Employer Branding & IC Manager”. [file:16]
- Safety:
  - If `safetyFlags` indicate off‑topic or policy violation, render a small system message explaining the simulation focus (HRM & leadership at Gucci) and gently redirect the user. [file:16]

---

## 5. Development Commands

```bash
# Install deps
cd frontend
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

This guide is intentionally concise and code‑oriented so reviewers can quickly understand how the UI maps to the AI Co‑worker and Director engine described in the assignment. [file:16]
```