// Supabase client singleton
// ---
// Initializes and exports a single Supabase client instance
// using environment variables set in .env (Vite exposes VITE_ prefix).

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!supabaseUrl || !supabaseAnonKey) {
    console.error(
        'Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY environment variables. ' +
        'Please set them in your .env file.'
    );
}

// Fallback dummy URL to prevent generic React crush if forgotten
const finalUrl = supabaseUrl?.startsWith('http') ? supabaseUrl : 'https://dummy.supabase.co';
const finalKey = supabaseAnonKey || 'dummy-key';

export const supabase = createClient(finalUrl, finalKey);
