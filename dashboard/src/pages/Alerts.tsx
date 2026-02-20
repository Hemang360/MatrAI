import { useEffect, useState } from 'react';
import { AlertTriangle, Phone, Clock } from 'lucide-react';
import { supabase, type Call } from '../lib/supabase';
import CallDetailModal from '../components/CallDetailModal';

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<Call[]>([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState<Call | null>(null);

    useEffect(() => {
        const load = async () => {
            try {
                const r = await supabase
                    .from('calls')
                    .select('*, users(phone, language)')
                    .eq('risk_level', 'RED')
                    .order('created_at', { ascending: false })
                    .limit(50);
                setAlerts(r.data ?? []);
            } finally {
                setLoading(false);
            }
        };
        load();

        // Live updates — push new RED alerts to top
        const ch = supabase
            .channel('red-alerts-live')
            .on(
                'postgres_changes',
                { event: 'INSERT', schema: 'public', table: 'calls', filter: "risk_level=eq.RED" },
                async (payload) => {
                    const { data } = await supabase
                        .from('calls')
                        .select('*, users(phone, language)')
                        .eq('id', payload.new.id)
                        .single();
                    if (data) setAlerts(prev => [data, ...prev]);
                }
            )
            .subscribe();

        return () => { supabase.removeChannel(ch); };
    }, []);

    return (
        <>
            <div className="space-y-6">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <AlertTriangle size={22} className="text-red-400" />
                        Red Alerts
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">
                        Calls that triggered an emergency triage result — click a card to review &amp; notify ASHA
                    </p>
                </div>

                {loading ? (
                    <div className="space-y-3">
                        {Array.from({ length: 3 }).map((_, i) => (
                            <div key={i} className="glass rounded-xl p-5 animate-pulse">
                                <div className="h-4 bg-slate-700 rounded w-48 mb-3" />
                                <div className="h-3 bg-slate-800 rounded w-full" />
                            </div>
                        ))}
                    </div>
                ) : alerts.length === 0 ? (
                    <div className="glass rounded-xl p-16 text-center">
                        <AlertTriangle size={48} className="text-slate-700 mx-auto mb-4" />
                        <p className="text-slate-400 font-medium">No red alerts</p>
                        <p className="text-slate-600 text-sm mt-1">
                            All calls have been low or moderate risk.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {alerts.map(alert => (
                            <button
                                key={alert.id}
                                onClick={() => setSelected(alert)}
                                className="w-full text-left glass rounded-xl p-5 border-l-4 border-red-500
                           shadow-lg shadow-red-500/5 hover:bg-slate-800/70
                           transition-colors group"
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-3 mb-2">
                                            <span className="badge-red">
                                                <AlertTriangle size={11} /> RED
                                            </span>
                                            <div className="flex items-center gap-1.5 text-xs text-slate-500">
                                                <Phone size={12} />
                                                <span className="font-medium text-slate-300">
                                                    {alert.users?.phone ?? 'Unknown'}
                                                </span>
                                            </div>
                                        </div>
                                        {alert.ai_advice && (
                                            <p className="text-sm text-slate-300 leading-relaxed line-clamp-2">
                                                {alert.ai_advice}
                                            </p>
                                        )}
                                    </div>

                                    <div className="shrink-0 flex flex-col items-end gap-2">
                                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                                            <Clock size={12} />
                                            {new Date(alert.created_at).toLocaleDateString('en-IN', {
                                                day: '2-digit', month: 'short', year: 'numeric',
                                                hour: '2-digit', minute: '2-digit'
                                            })}
                                        </div>
                                        <span className="text-xs text-slate-600 group-hover:text-brand-400
                                     transition-colors">
                                            Click to view details →
                                        </span>
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal */}
            {selected && (
                <CallDetailModal
                    call={selected}
                    onClose={() => setSelected(null)}
                />
            )}
        </>
    );
}
