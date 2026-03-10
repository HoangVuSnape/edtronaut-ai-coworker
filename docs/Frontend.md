# Frontend – AI Co‑worker Simulation

This frontend implements the UI layer for the **Edtronaut AI Co‑worker Engine**.  
It provides a simulation environment where learners chat with multiple AI co‑workers (CEO, CHRO, Employer Branding & IC) and receive subtle guidance from a Director agent.

---

## 1. Project Structure

```text
frontend/
├── package.json
├── src/
│   ├── App.tsx                  # Root component, wires layout + providers
│   ├── lib/
│   │   └── supabaseClient.ts    # Supabase Client for Authentication
│   ├── api/
│   │   ├── grpc_client.ts       # gRPC(-web) client to backend chat service
│   │   └── rest_client.ts       # REST fallback client (for local/dev)
│   ├── components/
│   │   ├── Auth/
│   │   │   └── Login.tsx        # Authentication UI (Google OAuth)
│   │   ├── ChatWindow.tsx       # Conversation UI (history + input box)
│   │   ├── NpcTogglePanel.tsx   # Toggle + select active NPC (CEO/CHRO/EB&IC)
│   │   ├── HintBanner.tsx       # Displays Director hints when user is stuck
│   │   └── SimulationLayout.tsx # High-level layout combining all widgets
│   └── styles/                  # Global styles / CSS
└── public/
    └── index.html
```

Design goals:
- Single‑page chat experience tailored to the Gucci HRM simulation.
- Clear separation between **transport layer** (`api/`), **domain logic/auth** (`lib/`), and **presentation components** (`components/`).
- Secure management of external Identity Providers (Google) via Supabase.

---

## 2. Authentication & Data Flow

### 2.1. Supabase Authentication
We rely on **Supabase** for user lifecycle and identity management.
- `Login.tsx` handles `supabase.auth.signInWithOAuth({ provider: 'google' })`.
- A global `AuthProvider` wraps the application, listening to `onAuthStateChange`.
- Once authenticated, the frontend retrieves the active `access_token` (JWT).

### 2.2. API Layer Delivery
Every request made to the Backend must carry the `access_token`. 

When communicating over **REST**:
```ts
export async function sendMessageRest(req: ChatRequest, token: string): Promise<ChatResponse> {
  const res = await fetch(`/api/npc/${req.npcId}/chat`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}` 
    },
    body: JSON.stringify({ sessionId: req.sessionId, message: req.message }),
  });
  return res.json();
}
```
*Note: The gRPC-web implementation follows a similar metadata injection pattern for its Bearer tokens.*

### 2.3. Session & NPC Simulation Flow
1. **User Types**: User submits a message via the `ChatWindow`.
2. **Dispatch**: `SimulationLayout` grabs the active JWT and calls the API (either REST or gRPC).
3. **Response**: The Backend processes the chat (verifying the JWT), traces via Langfuse, generates an AI response via RAG/LLM, and returns it.
4. **State Update**: The chat UI updates, appending the `assistantMessage` and optionally displaying a `hint` in the `HintBanner`.

---

## 3. Core Components

### 3.1. SimulationLayout
Top‑level layout component. Responsible for owning session‑level state (`sessionId`, `messages`, `enabledNpcIds`, `activeNpcId`, `hint`) and orchestrating communication with the backend.

### 3.2. ChatWindow
Renders full conversation history. Visually distinguishes between the user and specific NPCs (CEO vs CHRO).

### 3.3. NpcTogglePanel
Encodes the physical “AI coworkers (toggle on/off)” requirement. Allows users to switch between talking to the CHRO, CEO, or EB&IC. 

### 3.4. HintBanner
Visualizes the Director agent layer without breaking immersion. Only visible when a non‑empty `hint` is intercepted from the backend payload.

---

## 4. Development Commands

```bash
# Install deps
cd frontend
npm install

# Run dev server
npm run dev

# Build for production
npm run build
```

*Be sure to set your Supabase `.env` variables (`VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`) locally before running the dev server.*