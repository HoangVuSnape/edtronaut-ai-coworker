# Testing Strategy: "Mock the Expensive, Test the Logic"

## 1. Overview
GenAI applications are notoriously hard to test because LLMs are non-deterministic, slow, and expensive. Our strategy mocks the LLM layer for unit tests and strictly separates "Logic Tests" from "Integration Tests".

---

## 2. Test Pyramid

### 2.1. Unit Tests (Fast & Cheap)
**Scope**: Domain Logic, State Transitions, Rule Engines.
**Tools**: `pytest`, `unittest.mock`.
**Rule**: NEVER call OpenAI/Anthropic in unit tests.

**What to Test:**
*   **ChatService**: Given a specific `UserMessage`, does it correctly create a `Turn` object? Does it call `save_conversation`?
*   **SessionManager**: Does it correctly serialize/deserialize the `Conversation` model?
*   **Prompt Builders**: Given a context, does the prompt string match the expected template?

**Mocking Pattern:**
```python
# tests/test_chat_service.py
@patch("infrastructure.llm_providers.OpenAIClient")
def test_process_message(mock_llm):
    # Setup
    mock_llm.generate.return_value = "Hello, I am the Gucci CEO."
    service = ChatService(llm_client=mock_llm)
    
    # Act
    response = service.process_message("Hi")
    
    # Assert
    assert response.content == "Hello, I am the Gucci CEO."
    mock_llm.generate.assert_called_once()
```

### 2.2. Integration Tests (Connected Components)
**Scope**: Database, Redis, Vector Store.
**Tools**: `testcontainers` (Docker).
**Rule**: Spin up *real* database instances, but keep LLMs mocked.

**Scenario**:
*   Save a `Conversation` to the real PostgreSQL container.
*   Read it back.
*   Assert data integrity.

### 2.3. End-to-End (E2E) / "Golden Path"
**Scope**: Full User Journey.
**Tools**: Custom script or `pytest` with `--e2e` flag.
**Rule**: Only run these manually or on specialized CI pipelines (Nightly).

---

## 3. Specialized GenAI Testing

### 3.1. Golden Datasets (Regression Testing)
To prevent "Refactor Regressions" (making the bot dumber), we maintain a dataset of **Input -> Expected Intent/Behavior**.

*   **File**: `tests/data/golden_conversations.json`
*   **Evaluator**: Uses `LLM-as-a-Judge` (via LangFuse) to grade the new response against the Golden response.

### 3.2. Deterministic Tool Testing
Tools like `KPI_Calculator` must be tested purely deterministically.
*   Input: `Revenue=100, Cost=50`
*   Expected: `Profit=50` (Exact match).

---

## 4. CI/CD Pipeline Rules

1.  **Commit/PR**: Run All Unit Tests + Linting. (Must pass 100%).
2.  **Nightly**: Run Integration Tests + Golden Dataset Evaluation.
3.  **Merge**: Requires approval if specific coverage metrics drop.
