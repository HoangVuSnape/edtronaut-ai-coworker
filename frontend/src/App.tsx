// Main App component
// ---
// Root component that wires the SimulationLayout with global providers.
// Switch between gRPC and REST clients via the USE_GRPC flag below.

import { useState, useEffect } from 'react';
import { SimulationLayout } from './components/SimulationLayout';
import { getToken, clearToken, login, getAuthHeaders } from './api/auth';
import './styles/global.css';

/**
 * Configuration flag – set to `false` to use the REST fallback client
 * instead of gRPC-web. In production this should be driven by an
 * environment variable (e.g. `import.meta.env.VITE_USE_GRPC`).
 */
export const USE_GRPC = true;

/**
 * Validate existing token by making a lightweight authenticated request.
 * Returns true if the token is still valid, false otherwise.
 */
async function validateToken(): Promise<boolean> {
    const token = getToken();
    if (!token) return false;

    try {
        const res = await fetch('/api/users', {
            method: 'GET',
            headers: { ...getAuthHeaders() },
        });
        // 401 or 403 means token is invalid/expired
        if (res.status === 401 || res.status === 403) {
            return false;
        }
        return true;
    } catch {
        // Network error — can't validate, assume invalid
        return false;
    }
}

export default function App() {
    const [ready, setReady] = useState(false);
    const [error, setError] = useState<string | undefined>();

    useEffect(() => {
        let cancelled = false;

        async function init() {
            // If we have a stored token, validate it first
            if (getToken()) {
                const isValid = await validateToken();
                if (isValid) {
                    if (!cancelled) setReady(true);
                    return;
                }
                // Token is invalid/expired – clear it and re-login
                clearToken();
            }

            // Auto-login with default admin credentials
            try {
                await login('admin@test.com', 'Admin@123');
                if (!cancelled) setReady(true);
            } catch {
                if (!cancelled) setError('Login failed. Please check backend.');
            }
        }

        init();
        return () => { cancelled = true; };
    }, []);

    if (error) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#ff4d4d', fontFamily: 'sans-serif' }}>
                ⚠️ {error}
            </div>
        );
    }

    if (!ready) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#aaa', fontFamily: 'sans-serif' }}>
                Authenticating…
            </div>
        );
    }

    return (
        <>
            <SimulationLayout />
        </>
    );
}
