import { useEffect, useState } from 'react';
import { AlertTriangle, Phone, Clock } from 'lucide-react';
import { supabase, type Call } from '../lib/supabase';

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<Call[]>([]);
    const [loading, setLoading] = useState(true);

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
    }, []);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <AlertTriangle size={22} className="text-red-400" />
                    Red Alerts
                </h1>
                <p className="text-slate-400 text-sm mt-1">
                    Calls that triggered an emergency triage result
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
                        <div
                            key={alert.id}
                            className="glass rounded-xl p-5 border-l-4 border-red-500
                         shadow-lg shadow-red-500/5"
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
                                        <p className="text-sm text-slate-300 leading-relaxed mb-3">
                                            {alert.ai_advice}
                                        </p>
                                    )}

                                    {alert.transcript && (
                                        <details className="group">
                                            <summary className="text-xs text-slate-500 cursor-pointer
                                         hover:text-slate-300 transition-colors list-none
                                         flex items-center gap-1">
                                                <span className="border border-slate-700 rounded px-2 py-0.5
                                         hover:border-slate-500">
                                                    View transcript
                                                </span>
                                            </summary>
                                            <pre className="mt-3 text-xs text-slate-400 bg-slate-900 rounded-lg
                                      p-4 overflow-x-auto whitespace-pre-wrap font-mono
                                      leading-relaxed">
                                                {alert.transcript}
                                            </pre>
                                        </details>
                                    )}
                                </div>

                                <div className="shrink-0 flex items-center gap-1.5 text-xs text-slate-500">
                                    <Clock size={12} />
                                    {new Date(alert.created_at).toLocaleDateString('en-IN', {
                                        day: '2-digit', month: 'short', year: 'numeric',
                                        hour: '2-digit', minute: '2-digit'
                                    })}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
