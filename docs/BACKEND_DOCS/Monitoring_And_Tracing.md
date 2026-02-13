# Monitoring & Observability with LangFuse

## Overview
We use **LangFuse** for end-to-end observability of our LLM application. It allows us to trace execution paths, debug complex agent interactions, manage prompts, and evaluate the quality of our AI Coworkers (NPCs).

## Integration Strategy

### 1. Tracing (The "Black Box" Recorder)
Every interaction in the `Application Layer` should be wrapped in a trace.

**Heirarchy:**
*   **Trace**: Corresponds to one full Turn (User Request -> Response).
    *   **Span (Application)**: `chat_service.process_message`
    *   **Span (LangGraph)**: The entire graph execution.
        *   **Generation (LLM)**: The specific call to OpenAI/Anthropic for the NPC.
        *   **Generation (LLM)**: The specific call for the Director/Evaluator.
        *   **Span (RAG)**: The retrieval process.

### 2. Setup (Python SDK)
In `infrastructure/monitoring/tracing.py`:

```python
from langfuse.decorators import observe
from langfuse import Langfuse

# Initialize singleton
langfuse = Langfuse()

@observe(name="chat_interaction")
def process_chat_turn(user_input: str, context: dict):
    # Your logic here
    pass
```

### 3. Tagging & Metadata
Crucial for filtering traces in the LangFuse dashboard.

*   **`session_id`**: The conversation UUID.
*   **`user_id`**: The user's UUID.
*   **Tags**:
    *   `env:production` vs `env:staging`
    *   `persona:gucci_ceo`
    *   `scenario:negotiation_101`
    *   `model:gpt-4o`

### 4. Prompt Management
Instead of hardcoding prompts in `domain/prompts/`, we fetch them from LangFuse. This allows non-engineers to tweak personas without code deploys.

```python
# domain/prompts/gucci_ceo.py
def get_prompt():
    prompt = langfuse.get_prompt("gucci_ceo_persona", version="latest")
    return prompt.compile(trait="demanding")
```

---

## Quality Evaluation (Scores)

We use three layers of scoring to measure success:

### Level 1: User Feedback (Explicit)
When a user clicks "Thumbs Up/Down" in the UI.
```python
langfuse.score(
    trace_id=trace_id,
    name="user_satisfaction",
    value=1, # or 0
    comment="User liked the negotiation tip"
)
```

### Level 2: Model-Based Evaluation (Implicit/Director)
The **Director Agent** (implemented in `director_service.py`) automatically scores the NPC's response on specific criteria.
```python
# After NPC responds
score = director.evaluate(npc_response) # e.g., 0.85 for "Professionalism"
langfuse.score(
    trace_id=trace_id,
    name="professionalism",
    value=score
)
```

### Level 3: Dataset Testing (CI/CD)
We maintain a "Golden Dataset" of reference conversations in LangFuse.
1.  Define usage examples (Input: "I want a raise", Expected: "Professional pushback").
2.  Run these against the current Agent version.
3.  Compare results using LLM-as-a-judge.

---

## Alerting
*   Set up alerts in LangFuse for:
    *   **Cost Spikes**: If a session uses > $1.00.
    *   **High Latency**: If P99 response time > 10s.
    *   **Low Quality**: If average "user_satisfaction" drops below 0.7.
