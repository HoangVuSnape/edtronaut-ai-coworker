# Prompt Engineering Design & Caching Strategy

## 1. Overview
This document outlines the strategy for designing, managing, and optimizing prompts for the Edtronaut AI Coworker. It integrates principles from **Prompt Engineering**, **Prompt Caching**, and **Prompt Libraries** to ensure high-quality NPC personas, cost efficiency, and maintainability.

---

## 2. Prompt Architecture (The "Prompt Sandwich")

To maximize performance and cache hits, we structure our prompts in a specific order. This is critical for Anthropic's **Prefix Caching** and general LLM attention mechanisms.

### Structure
1.  **System Block** (Static - **CACHED**)
    *   **Persona Definition**: "You are the Gucci CEO..."
    *   **Core Rules**: "Never break character", "Be demanding but fair".
    *   **Response Format**: "Keep responses under 3 sentences unless asked."
2.  **Knowledge Block** (Semi-Static - **CACHED**)
    *   **Scenario Context**: "You are in a salary negotiation."
    *   **RAG Content**: Retrieved documents (Company Policy PDF chunks).
3.  **History Block** (Dynamic)
    *   `User: "Hello"`
    *   `Assistant: "What do you want?"`
4.  **Instruction Block** (Dynamic)
    *   **Current User Input**: "I want a raise."
    *   **Director Instructions**: (Hidden) "[Director Note: The user is being too passive. Push back hard.]"

---

## 3. Caching Strategy
We utilize **Anthropic's Prompt Caching** (or similar features in other providers) to reduce costs and latency.

### Rules for Caching
1.  **Structure for HITS**:
    *   Place the largest, most static content at the **top** of the prompt.
    *   Breakpoints are strictly defined. If we change one character in the System Block, the cache is invalidated.
2.  **The "2-Attempt" Cache**:
    *   **Attempt 1 (System)**: Cache the huge System Prompt + Base Scenario.
    *   **Attempt 2 (RAG)**: If the RAG context is large (>1024 tokens) and reused (e.g., a shared "Employee Handbook"), we cache it as a second specific checkpoint.

### Implementation Logic
```python
messages = [
    {
        "role": "system",
        "content": [
            {"type": "text", "text": BASE_PERSONA_TEXT, "cache_control": {"type": "ephemeral"}}
        ]
    },
    ...
]
```

---

## 4. Persona Design (Prompt Engineering)

### 4.1. The "Rich Persona" Template
Every NPC must be defined using the **Persona Pattern** with **Few-Shot Examples**.

**Template Components:**
*   **Identity**: Name, Role, Years of Experience.
*   **Psychographics**: MBTI, Big 5 Traits (e.g., "High Openness, Low Agreeableness").
*   **Communication Style**:
    *   *Tone*: Formal, casual, aggressive, passive-aggressive.
    *   *Quirks*: Uses metaphors, hates jargon, speaks in short bursts.
*   **Knowledge Boundary**: What they DO NOT know (to prevent hallucination).

**Example (Gucci CEO):**
```markdown
# Identity
You are Marco Bizzarri, CEO of Gucci. You are a visionary, decisive, and focused on "eclectic aesthetics."

# Style
- Direct and impatient with mediocrity.
- Use fashion business terminology (SKUs, merchandising, brand equity).
- rarely apologize.

# Few-Shot Examples
User: "I think we should delay the launch."
You: "Delay? In this industry, delay is death. Give me a solution, not a problem."
```

### 4.2. Chain-of-Thought (For Director Agent)
The **Director Agent** (Supervisor) uses CoT to analyze the conversation before acting.

**Prompt Pattern:**
```markdown
Analyze the last turn.
1. Identify the User's intent (e.g., trying to negotiate).
2. Assess the User's tone (confidence level).
3. Check against the "Winning Criteria" for this scenario.
4. Decide: Should I intervene?

Output as JSON.
```

---

## 5. Prompt Library & Management

### 5.1. Directory Structure
We version prompts as code, but sync with LangFuse.

```text
backend/src/coworker_api/domain/prompts/
├── __init__.py
├── base.py                 # Common instructions (Security, safety)
├── library/
│   ├── negotiation.py      # Task-specific phrases
│   └── feedback.py         # Formats for Director feedback
└── personas/
    ├── gucci_ceo/
    │   ├── system.md       # The core static prompt
    │   └── knowledge.md    # Static knowledge for this contact
    └── gucci_chro/
```

### 5.2. Governance
*   **No Magic Strings**: Never hardcode prompts in `chat_service.py`. Always import from `domain/prompts`.
*   **LangFuse Sync**: on startup, the application checks if `LangFuse` has a newer version of the prompt. If yes, it pulls it. If no, it uses the local file.
*   **Testing**: We utilize `evaluation_service` to run "Golden input" tests against new prompt versions to ensure the Persona hasn't "drifted".
