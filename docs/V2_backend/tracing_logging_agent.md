```markdown
# Logging & Agent Tracing with Langfuse Agent Graphs

This document describes how we log and trace the **AI Co‑worker Engine** using **Langfuse Agent Graphs**, so that each step of the Director + NPC + RAG + Tools pipeline appears as a node with clear edges and timing in the Langfuse UI. [file:17][web:28]

---

## 1. Goals

- Quan sát toàn bộ 1 lượt tương tác User → Director → NPC → RAG → Tools → Response dưới dạng **graph**. [file:17][web:28]  
- Mỗi node trong graph tương ứng với một bước logic rõ ràng trong agent graph (Director, NPC, RAG, Tool). [file:26][web:33]  
- Edges thể hiện **thứ tự thực thi** và latency giữa các bước, giúp debug chỗ chậm hoặc hành vi bất thường. [web:28][web:36]  

---

## 2. Conceptual Mapping

Một lượt chat trong simulation Gucci được map:

- **Trace**  
  - Một turn đầy đủ: request từ frontend → backend xử lý → final NPC reply. [file:17]

- **Observations (nodes)**  
  - `director_decision` – Director agent phân tích context, phát hiện stuck/off‑track. [file:26]  
  - `rag_retrieval` – RAG pipeline lấy context Gucci / competency framework. [file:20][web:37]  
  - `npc:<persona>` – NPC LLM call (CEO, CHRO, Employer Branding & IC). [file:23][file:25]  
  - `tool:<name>` – Tool call (KPI calculator, A/B simulator, portfolio exporter). [file:20]

- **Edges**  
  - Không khai báo thủ công, Langfuse suy ra từ:
    - `startTime` / `endTime` của từng observation.
    - `parentObservationId` (nesting). [web:28]

Ví dụ target graph cho 1 turn:

`__start__ → director_decision → rag_retrieval → npc:gucci_chro → tool:kpi_calculator → __end__`  

Mỗi node hiển thị latency riêng; edges thể hiện path thực thi qua thời gian. [web:28][web:36]

---

## 3. Directory & Module Layout

```text
backend/src/coworker_api/infrastructure/monitoring/
├── __init__.py
└── tracing.py        # Langfuse integration + helpers to create traces & nodes
```

- `tracing.py` expose helpers để Application layer gọi:
  - `start_chat_trace(session_id, user_id, persona_id)`  
  - `log_director_node(...)`  
  - `log_rag_node(...)`  
  - `log_npc_node(...)`  
  - `log_tool_node(...)`  

---

## 4. Implementation Details

### 4.1. Trace & Node Helpers

```python
# infrastructure/monitoring/tracing.py
from langfuse import Langfuse

langfuse = Langfuse()

def start_chat_trace(session_id: str, user_id: str | None, persona_id: str):
    """
    Create a trace for one chat turn. Called once per user message.
    """
    trace = langfuse.trace(
        name="chat_turn",
        session_id=session_id,
        user_id=user_id,
        metadata={"persona_id": persona_id},
        tags=[
            f"persona:{persona_id}",
            "layer:chat_service",
            # env, model, scenario can be added here
        ],
    )
    return trace

def log_director_node(trace, input_text: str, decision: dict):
    """
    Node: Director Agent analysis.
    """
    obs = trace.observation(
        type="observation",              # required for Agent Graphs
        name="director_decision",
        input=input_text,
        output=decision,
        metadata={"layer": "director"},
    )
    return obs

def log_rag_node(trace, parent_obs, query: str, docs: list[dict]):
    """
    Node: RAG retrieval.
    """
    obs = trace.observation(
        type="observation",
        name="rag_retrieval",
        input=query,
        output={"docs": docs},
        parent_observation_id=parent_obs.id,
        metadata={"layer": "rag"},
    )
    return obs

def log_npc_node(trace, parent_obs, persona_id: str, prompt: str, response: str):
    """
    Node: NPC LLM call.
    """
    obs = trace.observation(
        type="observation",
        name=f"npc:{persona_id}",
        input=prompt,
        output=response,
        parent_observation_id=parent_obs.id,
        metadata={"layer": "npc", "persona_id": persona_id},
    )
    return obs

def log_tool_node(trace, parent_obs, tool_name: str, args: dict, result: dict):
    """
    Node: Tool execution.
    """
    obs = trace.observation(
        type="observation",
        name=f"tool:{tool_name}",
        input=args,
        output=result,
        parent_observation_id=parent_obs.id,
        metadata={"layer": "tool"},
    )
    return obs
```

Key points:

- `type="observation"`: để Langfuse xem đây là node trong Agent Graph, không chỉ là span/generation. [web:28]  
- `parent_observation_id`: định nghĩa nesting, giúp Langfuse vẽ edge parent → child. [web:28]  

### 4.2. Edges & Timing on Agent Graph

Langfuse Agent Graph suy ra edges tự động:

- Nếu observation B có `parentObservationId = A.id` và start sau A, graph sẽ vẽ **A → B**. [web:28]  
- `startTime` / `endTime` của mỗi observation được SDK set khi bạn tạo + kết thúc node, từ đó UI hiển thị:
  - Latency của node (duration = `endTime - startTime`).  
  - Thứ tự các bước trong timeline và trên graph (như ví dụ `__start__`, `agent`, `tools`, `__end__`). [web:31][web:36]

Để timing/edge hiển thị chính xác:

- Tạo observation **ngay trước** khi step bắt đầu và để SDK handle kết thúc khi hàm return.  
- Không gom nhiều step logic khác nhau vào chung một observation nếu muốn thấy chúng tách node trên graph. [web:29]

---

## 5. Wiring Tracing into the Agent Orchestration

Application layer (`application/chat_service.py`) orchestrates Director → RAG → NPC → Tools. [file:25][file:26]  
Tại đây chúng ta gọi các helper tracing để tạo graph.

```python
# application/chat_service.py
from coworker_api.infrastructure.monitoring.tracing import (
    start_chat_trace,
    log_director_node,
    log_npc_node,
    log_rag_node,
    log_tool_node,
)

def process_chat_turn(request: ChatRequest) -> ChatResponse:
    # 0) Create one trace per turn
    trace = start_chat_trace(
        session_id=request.session_id,
        user_id=request.user_id,
        persona_id=request.npc_id,
    )

    # 1) Director analyzes user message + scenario state
    director_decision = director_service.analyze(request)
    director_obs = log_director_node(
        trace=trace,
        input_text=request.message,
        decision=director_decision,
    )

    # 2) RAG retrieves Gucci/HRM context
    rag_docs = retriever.retrieve(
        request.message,
        persona_id=request.npc_id,
    )
    rag_obs = log_rag_node(
        trace=trace,
        parent_obs=director_obs,
        query=request.message,
        docs=[{"id": d.id, "score": d.score} for d in rag_docs],
    )

    # 3) NPC builds prompt + calls LLM
    npc_prompt = npc_agent.build_prompt(
        request=request,
        docs=rag_docs,
        director_decision=director_decision,
    )
    npc_response = npc_agent.generate(npc_prompt)
    npc_obs = log_npc_node(
        trace=trace,
        parent_obs=rag_obs,
        persona_id=request.npc_id,
        prompt=npc_prompt,
        response=npc_response,
    )

    # 4) Optional tool call (KPI, A/B, portfolio)
    if director_decision.force_tool:
        tool_result = tools.run(
            director_decision.force_tool,
            npc_response=npc_response,
            context=director_decision.context,
        )
        log_tool_node(
            trace=trace,
            parent_obs=npc_obs,
            tool_name=director_decision.force_tool,
            args={"npc_response": npc_response},
            result=tool_result,
        )

    # 5) Attach final output to trace for quick view
    trace.update(output={"final_response": npc_response})

    return ChatResponse(
        message=npc_response,
        hint=director_decision.hint,
        safety_flags=director_decision.safety_flags,
    )
```

Kết quả trên Langfuse:

- Trace `chat_turn` chứa chain observation:
  - `director_decision` → `rag_retrieval` → `npc:gucci_chro` → `tool:kpi_calculator`.  
- Agent Graph view hiển thị node + edge theo đúng thời gian thực thi. [web:28][web:33]

---

## 6. Logging Conventions (Beyond Traces)

Song song với trace, chúng ta log JSON ra logger hệ thống (stdout / log collector) để dễ grep:

- **Fields chuẩn** trên mọi log entry liên quan đến agent:

  - `trace_id` – ID của Langfuse trace.  
  - `observation_id` – node ID, nếu log gắn với node cụ thể.  
  - `session_id` – session simulation.  
  - `persona_id` – `gucci_ceo | gucci_chro | gucci_eb_ic`. [file:16]  
  - `layer` – `director | npc | rag | tool | api`.  
  - `duration_ms` – latency của step (đồng bộ với Langfuse).  

Ví dụ:

```python
logger.info(
    "npc_response",
    extra={
        "trace_id": trace.id,
        "observation_id": npc_obs.id,
        "session_id": request.session_id,
        "persona_id": request.npc_id,
        "layer": "npc",
        "duration_ms": duration_ms,
    },
)
```

Logging truyền thống + Agent Graphs giúp:

- Tìm nhanh traces liên quan đến lỗi (theo `session_id`, `persona_id`).  
- Drill‑down vào node chậm trong graph (RAG hay Tool). [web:36]

---

## 7. Tagging & Metadata Strategy

Để dễ filter trên Langfuse dashboard: [file:17][web:28]

- Tags gợi ý:
  - `env:local | env:staging | env:prod`  
  - `simulation:gucci_hrm_v2`  
  - `persona:gucci_ceo | persona:gucci_chro | persona:gucci_eb_ic`  
  - `model:gpt-4o | model:claude-3-5`  

- Metadata thêm vào trace:
  - `scenario_id`, `attempt_number`, `user_segment`, v.v.  

Điều này giúp đội ngũ Edtronaut lọc trace theo simulation, persona hoặc bản model khi debug/so sánh. [file:16][web:29]

---

## 8. References

- Langfuse Docs – **Agent Graphs**: cách họ xây graph từ observations, timing và nesting. [web:28]  
- Langfuse Cookbook – **Trace & Evaluate LangGraph Agents**: ví dụ tích hợp LangGraph + Langfuse để visualize agent execution. [web:33]

This logging & tracing setup ensures the AI Co‑worker Engine is observable như một **agentic graph** thực thụ, phù hợp với kiến trúc LangGraph và yêu cầu debugging của hệ thống mô phỏng công việc. [file:17][file:26][web:37]
```