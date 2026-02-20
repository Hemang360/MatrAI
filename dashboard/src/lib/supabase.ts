import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY as string;

if (!supabaseUrl || !supabaseKey) {
    console.error(
        '[MatrAI] VITE_SUPABASE_URL or VITE_SUPABASE_KEY not set in .env.local'
    );
}

export const supabase = createClient(supabaseUrl, supabaseKey);

// ---------------------------------------------------------------------------
// Type definitions matching the Supabase schema (db/migrations.sql)
// ---------------------------------------------------------------------------

export type RiskLevel = 'RED' | 'YELLOW' | 'GREEN';

export interface User {
    id: string;
    phone: string;
    language: string;
    consent_given: boolean;
    created_at: string;
}

export interface Call {
    id: string;
    user_id: string;
    risk_level: RiskLevel | null;
    symptoms_json: Record<string, unknown> | null;
    transcript: string | null;
    ai_advice: string | null;
    created_at: string;
    // Joined fields (when fetching with user data)
    users?: Pick<User, 'phone' | 'language'>;
}

export interface EmergencyLog {
    id: string;
    call_id: string;
    user_id: string;
    notified_asha: boolean;
    created_at: string;
}

// ---------------------------------------------------------------------------
// Query helpers
// ---------------------------------------------------------------------------

/** Fetch the 100 most recent calls with the caller's phone number joined */
export async function fetchRecentCalls(limit = 100) {
    return supabase
        .from('calls')
        .select('*, users(phone, language)')
        .order('created_at', { ascending: false })
        .limit(limit);
}

/** Fetch dashboard summary stats */
export async function fetchStats() {
    const [calls, users, red, emergency] = await Promise.all([
        supabase.from('calls').select('id', { count: 'exact', head: true }),
        supabase.from('users').select('id', { count: 'exact', head: true }),
        supabase
            .from('calls')
            .select('id', { count: 'exact', head: true })
            .eq('risk_level', 'RED'),
        supabase
            .from('emergency_logs')
            .select('id', { count: 'exact', head: true }),
    ]);

    return {
        totalCalls: calls.count ?? 0,
        totalUsers: users.count ?? 0,
        redAlerts: red.count ?? 0,
        emergencyLogs: emergency.count ?? 0,
    };
}

/** Fetch all registered users */
export async function fetchUsers(limit = 100) {
    return supabase
        .from('users')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(limit);
}
