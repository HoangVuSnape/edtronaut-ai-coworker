# Diagrams – Backend Architecture

> Mermaid flowchart diagrams generated from the source code and `docs/BACKEND_DOCS_V2` documentation.
> All diagrams use `flowchart TB` (top-to-bottom) layout and can be expanded as the system evolves.

---

## Index

| # | File | Description |
|---|------|-------------|
| 01 | [01_high_level_architecture.md](./01_high_level_architecture.md) | Full system overview: all layers + external services |
| 02 | [02_chat_request_flow.md](./02_chat_request_flow.md) | End-to-end chat request lifecycle (HTTP → LLM → storage) |
| 03 | [03_domain_layer.md](./03_domain_layer.md) | Domain models, ports/interfaces, exceptions, prompt registry |
| 04 | [04_application_layer.md](./04_application_layer.md) | Application services and their port dependencies |
| 05 | [05_security_auth_flow.md](./05_security_auth_flow.md) | JWT login, token validation, role-based authorization |
| 06 | [06_rag_pipeline.md](./06_rag_pipeline.md) | RAG ingest pipeline + chat-time retrieval pipeline |
| 07 | [07_database_storage.md](./07_database_storage.md) | Redis · PostgreSQL · Qdrant storage architecture |
| 08 | [08_observability_tracing.md](./08_observability_tracing.md) | Langfuse trace spans and structured logging |
| 09 | [09_infrastructure_layer.md](./09_infrastructure_layer.md) | Detailed infrastructure module map |

---

## Diagram Types Used

```
flowchart TB   – top-to-bottom layout
subgraph       – groups related components visually
-->            – solid arrow (direct call / data flow)
-.->           – dashed arrow (indirect reference / optional)
{"..."}        – decision / conditional node
[("...")]      – cylindrical shape for databases
```

## How to Expand

- Add a new `.md` file with `10_`, `11_`, … prefix for new diagrams.
- Each file should start with a `# Diagram XX – Title` heading and a `> Source:` reference.
- Use `subgraph` blocks to group layers clearly.
