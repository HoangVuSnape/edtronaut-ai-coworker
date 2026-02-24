// Main App component
// ---
// Root component that wires the SimulationLayout with global providers.
// Switch between gRPC and REST clients via the USE_GRPC flag below.

import { useState, useEffect } from 'react';
import { SimulationLayout } from './components/SimulationLayout';
import { getToken, login } from './api/auth';
import './styles/global.css';

/**
 * Configuration flag – set to `false` to use the REST fallback client
 * instead of gRPC-web. In production this should be driven by an
 * environment variable (e.g. `import.meta.env.VITE_USE_GRPC`).
 */
export const USE_GRPC = true;

export default function App() {
    const [ready, setReady] = useState(!!getToken());
    const [error, setError] = useState<string | undefined>();

    useEffect(() => {
        if (ready) return;
        // Auto-login with default admin credentials on first load
        login('admin@test.com', 'Admin@123')
            .then(() => setReady(true))
            .catch(() => setError('Login failed. Please check backend.'));
    }, [ready]);

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
