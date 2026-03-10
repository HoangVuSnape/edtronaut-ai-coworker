// Auth token management (Supabase-based)
// ---
// Provides helpers for getting the current Supabase JWT access token
// and auth headers for API calls to the backend.

import { supabase } from '../lib/supabaseClient';

/**
 * Get the current access token from Supabase session.
 * Returns null if not authenticated.
 */
export async function getToken(): Promise<string | null> {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token ?? null;
}

/**
 * Build Authorization headers using the current Supabase JWT.
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
    const token = await getToken();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
}

/**
 * Sign out the current user and clear the Supabase session.
 */
export async function clearToken(): Promise<void> {
    await supabase.auth.signOut();
}
