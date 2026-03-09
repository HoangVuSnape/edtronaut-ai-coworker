# Error Handling Standards & gRPC Mapping

## 1. Overview
This document enforces a standardized way to handle exceptions across the backend. We map Python's **Domain Exceptions** to specific **gRPC Status Codes** so the Frontend can react appropriately (e.g., show a login screen vs. a retry button).

---

## 2. Standard Mappings

| Python Domain Exception | gRPC Status Code | Description | Frontend Action |
| :--- | :--- | :--- | :--- |
| `pydantic.ValidationError` | `INVALID_ARGUMENT (3)` | Bad input format (missing field, wrong type). | Show form error. |
| `ConversationNotFoundError` | `NOT_FOUND (5)` | The requested session ID does not exist. | Redirect to Dashboard. |
| `UserNotAuthenticatedError` | `UNAUTHENTICATED (16)` | Missing or invalid JWT. | Redirect to Login. |
| `PermissionDeniedError` | `PERMISSION_DENIED (7)` | Valid user, but insufficient role (e.g., User -> Admin). | Show "Access Denied" toast. |
| `LLMConnectionError` | `UNAVAILABLE (14)` | OpenAI/External API is down/timeout. | Show "Retry" button. |
| `ContextWindowExceededError`| `RESOURCE_EXHAUSTED (8)`| Conversation too long for the model token limit. | Prompt user to "Summarize/Reset". |
| `UnexpectedError` (Catch-all)| `INTERNAL (13)` | Unhandled bug in our code. | Show generic "Oops" page + Report. |

---

## 3. Implementation (Error Interceptor)

Instead of `try/except` blocks in every service method, we use a **Global Error Interceptor** (`infrastructure/api/error_interceptor.py`).

### Logic
```python
class ErrorInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        try:
            return continuation(handler_call_details)
        except DomainException as e:
            # Domain-specific logic
            context.abort(e.grpc_code, e.message)
        except Exception as e:
            # Catch-all for crashes
            logging.error(f"Validation failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, "Internal Server Error")
```

---

## 4. Frontend Contract
The Backend MUST NOT return raw Python stack traces to the client in Production.
*   **Dev Mode**: Stack trace in `details`.
*   **Prod Mode**: Friendly message in `details`.

### Structuring Details
We use standard `google.rpc.Status` which supports attaching metadata.
*   **Field**: `retry_delay` (seconds) -> For `UNAVAILABLE` errors.
*   **Field**: `error_code` (internal string) -> e.g., `ERR_QUOTA_LIMIT`.
