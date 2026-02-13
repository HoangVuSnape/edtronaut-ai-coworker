# Security & Authentication Design

## 1. Overview
This document defines how we secure the gRPC API, authenticate users, and manage role-based access control (RBAC).

**Goal**: Zero-trust architecture where every request is authenticated and authorized before it touches the Domain Layer.

---

## 2. Authentication Flow (JWT)

### Mechanism
We use **JSON Web Tokens (JWT)** as the primary bearer token. The token is issued upon login and must be included in the metadata of every subsequent gRPC call.

### Token Payload
The JWT payload contains the essential user identity claims:
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000", // User UUID
  "email": "user@edtronaut.com",
  "role": "user", // or 'admin'
  "exp": 1678886400 // Expiration Timestamp
}
```

### Protocol (gRPC Metadata)
Clients act as follows:
1.  **Login**: Call `AuthService.Login(email, password)` -> Receive `access_token`.
2.  **Request**: Attach the token to the gRPC metadata header:
    *   Key: `authorization`
    *   Value: `Bearer <access_token>`

---

## 3. Server-Side Implementation (Interceptors)

We employ a **Global Authentication Interceptor** in `infrastructure/api/grpc_interceptor.py` that runs *before* any service logic.

### Logic Flow
1.  **Intercept**: Catch the incoming gRPC call.
2.  **Extract**: Look for the `authorization` header.
3.  **Validate**:
    *   Missing header? -> `Abort(UNAUTHENTICATED)`
    *   Invalid signature? -> `Abort(UNAUTHENTICATED)`
    *   Expired? -> `Abort(UNAUTHENTICATED)`
4.  **Inject Context**: If valid, decode the JWT and inject the `user_id` and `role` into the **gRPC Context**.
    *   `context.user_id = token['sub']`
    *   `context.role = token['role']`
5.  **Proceed**: Allow the request to reach the `ChatService`.

---

## 4. Authorization (RBAC)

Not all authenticated users can do everything. We enforce permissions using a decorator pattern on the service methods.

### Decorator Usage
```python
# infrastructure/api/grpc_server.py

class DocumentService(DocumentServiceServicer):
    @requires_role("admin")
    def IngestDocument(self, request, context):
        # Only admins reach here
        pass

    @requires_role("user")
    def Chat(self, request, context):
        # Regular users reach here
        pass
```

---

## 5. Security Best Practices

1.  **TLS/SSL**: All gRPC traffic MUST be encrypted via TLS in production. The interceptor should reject non-secure connections in Prod.
2.  **Short-Lived Tokens**: Access tokens expire in 15 minutes. Use a `RefreshToken` flow to get new ones without re-entering credentials.
3.  **Password Hashing**: Store passwords using `Argon2` or `BCrypt`. NEVER plain text.
4.  **Rate Limiting**: (Implemented in Redis) Limit login attempts to 5 per minute to prevent brute-force attacks.
