import { useEffect, useState } from 'react';
import { PhoneCall, Users, AlertTriangle, Activity } from 'lucide-react';
import { fetchStats, fetchRecentCalls, type Call } from '../lib/supabase';
import RiskBadge from '../components/RiskBadge';

interface Stat {
    label: string;
    value: number;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    color: string;
    shadow: string;
}

export default function DashboardPage() {
    const [stats, setStats] = useState({ totalCalls: 0, totalUsers: 0, redAlerts: 0, emergencyLogs: 0 });
    const [calls, setCalls] = useState<Call[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([fetchStats(), fetchRecentCalls(5)])
            .then(([s, c]) => {
                setStats(s);
                setCalls(c.data ?? []);
            })
            .finally(() => setLoading(false));
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
                        {loading ? (
                            <div className="h-8 w-16 bg-slate-700 animate-pulse rounded" />
                        ) : (
                            <p className={`text-3xl font-bold ${color}`}>{value}</p>
                        )}
                    </div>
                ))}
            </div>

            {/* Recent Calls */}
            <div className="glass rounded-xl overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-700/50">
                    <h2 className="font-semibold text-white">Recent Calls</h2>
                </div>
                <div className="divide-y divide-slate-700/50">
                    {loading ? (
                        Array.from({ length: 3 }).map((_, i) => (
                            <div key={i} className="px-5 py-4 flex items-center gap-4 animate-pulse">
                                <div className="w-10 h-10 bg-slate-700 rounded-full" />
                                <div className="flex-1 space-y-2">
                                    <div className="h-3.5 bg-slate-700 rounded w-32" />
                                    <div className="h-3 bg-slate-800 rounded w-48" />
                                </div>
                            </div>
                        ))
                    ) : calls.length === 0 ? (
                        <div className="px-5 py-10 text-center text-slate-500">
                            No calls yet. Make a test call!
                        </div>
                    ) : (
                        calls.map(call => (
                            <div key={call.id} className="px-5 py-4 flex items-center gap-4 glass-hover">
                                <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center
                                justify-center shrink-0">
                                    <PhoneCall size={16} className="text-slate-400" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-white truncate">
                                        {call.users?.phone ?? 'Unknown caller'}
                                    </p>
                                    <p className="text-xs text-slate-500 truncate mt-0.5">
                                        {call.ai_advice?.slice(0, 80) ?? 'No advice recorded'}
                                    </p>
                                </div>
                                <div className="flex items-center gap-3 shrink-0">
                                    <RiskBadge level={call.risk_level} />
                                    <span className="text-xs text-slate-500">
                                        {new Date(call.created_at).toLocaleDateString('en-IN', {
                                            day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                                        })}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
