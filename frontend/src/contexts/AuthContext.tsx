// Auth Context Provider
// ---
// Provides Supabase auth state to the entire app via React Context.
// Handles session initialization, auth state changes, and sign-out.

import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabaseClient';

interface AuthContextType {
    session: Session | null;
    user: User | null;
    loading: boolean;
    signOut: () => Promise<void>;
    getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType>({
    session: null,
    user: null,
    loading: true,
    signOut: async () => {},
    getAccessToken: async () => null,
});

export function useAuth(): AuthContextType {
    return useContext(AuthContext);
}

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // 1. Check existing session on mount
        supabase.auth.getSession().then(({ data: { session } }) => {
            setSession(session);
            setLoading(false);
        });

        // 2. Listen for auth state changes (login, logout, token refresh)
        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, session) => {
            setSession(session);
            setLoading(false);
        });

        return () => subscription.unsubscribe();
    }, []);

    const signOut = useCallback(async () => {
        await supabase.auth.signOut();
        setSession(null);
    }, []);

    const getAccessToken = useCallback(async (): Promise<string | null> => {
        const { data: { session } } = await supabase.auth.getSession();
        return session?.access_token ?? null;
    }, []);

    return (
        <AuthContext.Provider
            value={{
                session,
                user: session?.user ?? null,
                loading,
                signOut,
                getAccessToken,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}
