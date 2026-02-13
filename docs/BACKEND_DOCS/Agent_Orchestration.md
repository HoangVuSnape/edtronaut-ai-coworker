# Agent Orchestration with LangGraph

## Overview
We use **LangGraph** to orchestrate the complex state and control flow of our AI agents. Unlike simple chains, LangGraph allows us to build **stateful, cyclic, and multi-actor** applications, which is essential for simulating a realistic coworker environment.

## key Concepts for Our Architecture

### 1. State Definition (`AgentState`)
The state is the "memory" of the graph that is passed between nodes. For Edtronaut, it mimics the `Domain Layer` memory models.

```python
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

class AgentState(TypedDict):
    # Core conversation history (List of HumanMessage, AIMessage)
    messages: Annotated[List[AnyMessage], add_messages]
    
    # Context vars
    user_id: str
    scenario_id: str
    npc_persona: str  # e.g., "Gucci CEO"
    
    # Director/Supervisor feedback
    director_feedback: str | None
    
    # Internal flags
    is_conversation_end: bool
```

### 2. Nodes (The Actors)
Each node represents a distinct step in the workflow.

*   **`npc_node`**: The primary actor (e.g., Gucci CEO). It receives the history and generates a response based on its persona.
*   **`director_node`**: The supervisor. It runs *after* the NPC or User to analyze the interaction. It can inject instructions into the `director_feedback` field for the next turn.
*   **`tool_node`**: Executes deterministic tools (e.g., `KPI_Calculator`, `RAG_Retriever`).

### 3. The Graph Flow
We implement a **Human-in-the-loop** pattern where the graph pauses for user input, but we also have autonomous loops between the NPC and the Director.

**Basic Flow:**
`Start` -> `Retrieve Context (RAG)` -> `NPC Node` -> `Director Audit` -> `End/Wait for User`

### 4. Persistence (Memory)
We use a **Redis Checkpointer** to persist the graph state. This differentiates "Short-term Agent Memory" from "Long-term Database Storage".
*   **Checkpoint**: Saves the exact state of the graph after every node execution. allows us to "resume" a conversation days later.
*   **Thread ID**: Maps to our `session_id`.

---

## Implementation Patterns

### Designing the Graph
In `application/chat_service.py` (or a dedicated `graph_builder.py`):

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver # Replace with Redis for prod

# 1. Initialize
builder = StateGraph(AgentState)

# 2. Add Nodes
builder.add_node("npc", call_npc_model)
builder.add_node("director", call_director_model)
builder.add_node("rag", retrieve_documents)

# 3. Add Edges
builder.add_edge(START, "rag")
builder.add_edge("rag", "npc")
builder.add_edge("npc", "director")
builder.add_edge("director", END) # Or conditional edge back to NPC if revision needed

# 4. Compile with Persistence
memory = MemorySaver() # Use RedisSaver in production
graph = builder.compile(checkpointer=memory)
```

### Handling Multi-Turn Conversations
The graph is "invoked" for each user message. Because we use persistence, LangGraph automatically loads the previous state (messages) based on the `thread_id`.

```python
config = {"configurable": {"thread_id": "session_123"}}
response = graph.invoke(
    {"messages": [HumanMessage(content="Hello, CEO.")]}, 
    config=config
)
```

### Director Intervention (Reflexion)
The Director can "reject" an NPC's response if it violates safety guidelines or character consistency.

```python
def director_condition(state: AgentState):
    if state.get("director_feedback") and "REVISE" in state["director_feedback"]:
        return "npc" # Send back to NPC to retry
    return END

builder.add_conditional_edges("director", director_condition)
```

---

## Best Practices
1.  **Tiny State**: Keep the `AgentState` minimal. Don't store massive PDF content in the state; store references or retrieved chunks instead.
2.  **Streaming**: Use `.stream()` instead of `.invoke()` to stream tokens to the frontend for a responsive UI.
3.  **Error Handling**: Wrap node execution in try/catch blocks to prevent one bad LLM call from crashing the entire session.
