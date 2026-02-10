// Main App component
// ---
// Root component that wires the SimulationLayout with global providers.
// Switch between gRPC and REST clients via the USE_GRPC flag below.

import { SimulationLayout } from './components/SimulationLayout';
import './styles/global.css';

/**
 * Configuration flag – set to `false` to use the REST fallback client
 * instead of gRPC-web. In production this should be driven by an
 * environment variable (e.g. `import.meta.env.VITE_USE_GRPC`).
 */
export const USE_GRPC = true;

export default function App() {
    return (
        <>
            <SimulationLayout />
        </>
    );
}
