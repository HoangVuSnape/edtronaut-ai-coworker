// Auth token management
// ---
// Simple in-memory + localStorage token store for the frontend.
// Token is obtained from the login API and stored here.

const TOKEN_KEY = 'edtronaut_access_token';

export function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
}

export function getAuthHeaders(): Record<string, string> {
    const token = getToken();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
}

/**
 * Login and store the returned JWT token.
 */
export async function login(email: string, password: string): Promise<void> {
    const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
        throw new Error(`Login failed: ${res.status}`);
    }

    const data = await res.json();
    setToken(data.access_token);
}
