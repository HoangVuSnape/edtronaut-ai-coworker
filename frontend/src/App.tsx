// Main App component
// ---
// Root component that shows the Login page or the main SimulationLayout
// depending on the Supabase auth state.

import { SimulationLayout } from './components/SimulationLayout';
import Login from './components/Login';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import './styles/global.css';

/**
 * Configuration flag – set to `false` to use the REST fallback client
 * instead of gRPC-web. In production this should be driven by an
 * environment variable (e.g. `import.meta.env.VITE_USE_GRPC`).
 */
export const USE_GRPC = true;

/**
 * Inner component that reads auth state and renders accordingly.
 */
function AppContent() {
    const { session, loading } = useAuth();

    if (loading) {
        return (
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100vh',
                color: '#aaa',
                fontFamily: 'sans-serif',
            }}>
                Loading…
            </div>
        );
    }

    if (!session) {
        return <Login />;
    }

    return <SimulationLayout />;
}

export default function App() {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    );
}
