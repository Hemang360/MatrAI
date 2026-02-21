import { useEffect, useState } from 'react';
import { PhoneCall, Users, AlertTriangle, Activity } from 'lucide-react';
import { fetchStats } from '../lib/supabase';
import { supabase } from '../lib/supabase';
import CallLog from '../components/CallLog';

interface Stat {
    label: string;
    value: number;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    color: string;
    shadow: string;
}

export default function DashboardPage() {
    const [stats, setStats] = useState({ totalCalls: 0, totalUsers: 0, redAlerts: 0, emergencyLogs: 0 });
    const [loadingStats, setLoadingStats] = useState(true);

    useEffect(() => {
        const loadStats = () =>
            fetchStats().then(s => { setStats(s); setLoadingStats(false); });

        loadStats();

        // Refresh stat counts when a new call is inserted
        const ch = supabase
            .channel('stats-refresh')
            .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'calls' }, loadStats)
            .subscribe();

        return () => { supabase.removeChannel(ch); };
    }, []);


    const statCards: Stat[] = [
        { label: 'Total Calls', value: stats.totalCalls, icon: PhoneCall, color: 'text-brand-400', shadow: 'shadow-brand-500/20' },
        { label: 'Patients', value: stats.totalUsers, icon: Users, color: 'text-blue-400', shadow: 'shadow-blue-500/20' },
        { label: 'RED Alerts', value: stats.redAlerts, icon: AlertTriangle, color: 'text-red-400', shadow: 'shadow-red-500/20' },
        { label: 'Emergencies', value: stats.emergencyLogs, icon: Activity, color: 'text-amber-400', shadow: 'shadow-amber-500/20' },
    ];

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-white">Overview</h1>
                <p className="text-slate-400 text-sm mt-1">
                    Live summary of MatrAI health calls and patient data
                </p>
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {statCards.map(({ label, value, icon: Icon, color, shadow }) => (
                    <div key={label} className={`glass rounded-xl p-5 shadow-lg ${shadow}`}>
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">{label}</p>
                            <Icon size={18} className={color} />
                        </div>
                        {loadingStats ? (
                            <div className="h-8 w-16 bg-slate-700 animate-pulse rounded" />
                        ) : (
                            <p className={`text-3xl font-bold ${color}`}>{value}</p>
                        )}
                    </div>
                ))}
            </div>

            {/* Live Call Feed */}
            <CallLog limit={20} />

        </div>
    );
}
