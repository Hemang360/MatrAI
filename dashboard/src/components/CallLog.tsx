/**
 * CallLog — real-time call log with risk-based color coding.
 *
 * Updates via two mechanisms:
 *   1. Supabase Realtime (postgres_changes on INSERT in calls table)
 *      → instant push when a new call is saved by the backend
 *   2. 30-second polling safety net
 *      → catches any events Supabase Realtime might miss
 *
 * Sort order: RED first → YELLOW → GREEN → unknown, then newest within each tier.
 */
import { useEffect, useRef, useState } from 'react';
import { PhoneCall, Clock, Wifi } from 'lucide-react';
import { supabase, type Call } from '../lib/supabase';
import RiskBadge from './RiskBadge';

// Risk sort priority (lower = higher in list)
const RISK_PRIORITY: Record<string, number> = { RED: 0, YELLOW: 1, GREEN: 2 };
const riskPriority = (r: string | null) => RISK_PRIORITY[r ?? ''] ?? 3;

function sortCalls(calls: Call[]): Call[] {
    return [...calls].sort((a, b) => {
        const pd = riskPriority(a.risk_level) - riskPriority(b.risk_level);
        if (pd !== 0) return pd;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
}

function rowClass(risk: string | null): string {
    if (risk === 'RED') return 'row-red';
    if (risk === 'YELLOW') return 'row-yellow';
    return 'row-green';
}

interface CallLogProps {
    /** How many rows to show (default 50) */
    limit?: number;
    /** Optional search string to filter by phone */
    search?: string;
    /** Show expanded transcript on click */
    expandable?: boolean;
}

export default function CallLog({ limit = 50, search = '', expandable = true }: CallLogProps) {
    const [calls, setCalls] = useState<Call[]>([]);
    const [loading, setLoading] = useState(true);
    const [liveStatus, setLiveStatus] = useState<'connecting' | 'live' | 'poll'>('connecting');
    const [expanded, setExpanded] = useState<string | null>(null);
    const [newIds, setNewIds] = useState<Set<string>>(new Set()); // flash animation
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // -----------------------------------------------------------------------
    // Fetch helpers
    // -----------------------------------------------------------------------
    const fetchCalls = async () => {
        const { data } = await supabase
            .from('calls')
            .select('*, users(phone, language)')
            .order('created_at', { ascending: false })
            .limit(limit);
        if (data) setCalls(sortCalls(data));
        setLoading(false);
    };

    // -----------------------------------------------------------------------
    // Initial load + Supabase Realtime subscription
    // -----------------------------------------------------------------------
    useEffect(() => {
        fetchCalls();

        const channel = supabase
            .channel('calls-live')
            .on(
                'postgres_changes',
                { event: 'INSERT', schema: 'public', table: 'calls' },
                async (payload) => {
                    // New row arrived — fetch the full row (with joined phone number)
                    const { data } = await supabase
                        .from('calls')
                        .select('*, users(phone, language)')
                        .eq('id', payload.new.id)
                        .single();

                    if (data) {
                        setCalls(prev => sortCalls([data, ...prev].slice(0, limit)));
                        // Flash the new row for 3s
                        setNewIds(ids => new Set([...ids, data.id]));
                        setTimeout(() => {
                            setNewIds(ids => { const n = new Set(ids); n.delete(data.id); return n; });
                        }, 3000);
                    }
                }
            )
            .subscribe((status) => {
                if (status === 'SUBSCRIBED') {
                    setLiveStatus('live');
                } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
                    setLiveStatus('poll');
                    // Fall back to polling every 5s
                    pollRef.current = setInterval(fetchCalls, 5000);
                }
            });

        // 30-second safety-net poll regardless of realtime status
        const safetyPoll = setInterval(fetchCalls, 30_000);

        return () => {
            supabase.removeChannel(channel);
            clearInterval(safetyPoll);
            if (pollRef.current) clearInterval(pollRef.current);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // -----------------------------------------------------------------------
    // Client-side search filter
    // -----------------------------------------------------------------------
    const filtered = search
        ? calls.filter(c =>
            (c.users?.phone ?? '').toLowerCase().includes(search.toLowerCase()) ||
            (c.risk_level ?? '').toLowerCase().includes(search.toLowerCase()))
        : calls;

    // -----------------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------------
    return (
        <div className="glass rounded-xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3.5
                      border-b border-slate-700/50">
                <h2 className="font-semibold text-white text-sm">Live Call Feed</h2>
                <div className="flex items-center gap-2 text-xs">
                    {liveStatus === 'live' && (
                        <>
                            <span className="live-dot" />
                            <span className="text-emerald-400 font-medium">Live</span>
                        </>
                    )}
                    {liveStatus === 'poll' && (
                        <>
                            <Wifi size={12} className="text-amber-400" />
                            <span className="text-amber-400 font-medium">Polling</span>
                        </>
                    )}
                    {liveStatus === 'connecting' && (
                        <span className="text-slate-500">Connecting…</span>
                    )}
                </div>
            </div>

            {/* Column headers */}
            <div className="grid grid-cols-12 gap-3 px-5 py-2.5 border-b border-slate-800
                      text-xs font-medium text-slate-500 uppercase tracking-wide">
                <div className="col-span-2">Time</div>
                <div className="col-span-3">Phone</div>
                <div className="col-span-2">Risk</div>
                <div className="col-span-5">Summary / Advice</div>
            </div>

            {/* Rows */}
            <div className="divide-y divide-slate-800/60">
                {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="px-5 py-4 animate-pulse flex gap-4">
                            <div className="h-3.5 bg-slate-800 rounded w-full" />
                        </div>
                    ))
                ) : filtered.length === 0 ? (
                    <div className="px-5 py-14 text-center">
                        <PhoneCall size={36} className="text-slate-700 mx-auto mb-3" />
                        <p className="text-slate-500 text-sm">
                            {search ? 'No calls match your search.' : 'No calls yet — waiting for the first call…'}
                        </p>
                    </div>
                ) : (
                    filtered.map(call => {
                        const isNew = newIds.has(call.id);
                        return (
                            <div key={call.id}>
                                <button
                                    onClick={() => expandable && setExpanded(expanded === call.id ? null : call.id)}
                                    className={`
                    w-full grid grid-cols-12 gap-3 px-5 py-3.5 text-left
                    transition-all duration-300
                    ${rowClass(call.risk_level)}
                    ${isNew ? 'ring-1 ring-inset ring-brand-500/40' : ''}
                    ${expandable ? 'cursor-pointer hover:brightness-125' : 'cursor-default'}
                  `}
                                >
                                    {/* Time */}
                                    <div className="col-span-2 flex items-center gap-1.5 text-xs text-slate-400">
                                        <Clock size={11} className="shrink-0 text-slate-500" />
                                        <span>
                                            {new Date(call.created_at).toLocaleTimeString('en-IN', {
                                                hour: '2-digit', minute: '2-digit', hour12: true
                                            })}
                                            <br />
                                            <span className="text-slate-600">
                                                {new Date(call.created_at).toLocaleDateString('en-IN', {
                                                    day: '2-digit', month: 'short'
                                                })}
                                            </span>
                                        </span>
                                    </div>

                                    {/* Phone */}
                                    <div className="col-span-3 flex items-center gap-1.5">
                                        <PhoneCall size={11} className="text-slate-500 shrink-0" />
                                        <span className="text-sm font-medium text-slate-200 truncate">
                                            {call.users?.phone ?? '—'}
                                        </span>
                                    </div>

                                    {/* Risk */}
                                    <div className="col-span-2 flex items-center">
                                        <RiskBadge level={call.risk_level} />
                                    </div>

                                    {/* Summary */}
                                    <div className="col-span-5 text-xs text-slate-400 flex items-center truncate">
                                        <span className="truncate">
                                            {call.ai_advice?.slice(0, 90) ?? '—'}
                                        </span>
                                    </div>
                                </button>

                                {/* Expanded detail panel */}
                                {expandable && expanded === call.id && (
                                    <div className="px-5 pb-5 pt-3 bg-slate-900/60 space-y-4
                                  border-t border-slate-800/60">
                                        {call.ai_advice && (
                                            <div>
                                                <p className="text-xs font-semibold text-slate-500 uppercase
                                      tracking-wide mb-1.5">AI Advice</p>
                                                <p className="text-sm text-slate-300 leading-relaxed">
                                                    {call.ai_advice}
                                                </p>
                                            </div>
                                        )}
                                        {call.transcript && (
                                            <div>
                                                <p className="text-xs font-semibold text-slate-500 uppercase
                                      tracking-wide mb-1.5">Transcript</p>
                                                <pre className="text-xs text-slate-400 bg-slate-950 rounded-lg p-4
                                        overflow-x-auto whitespace-pre-wrap font-mono
                                        leading-relaxed max-h-64 overflow-y-auto">
                                                    {call.transcript}
                                                </pre>
                                            </div>
                                        )}
                                        {call.symptoms_json && Object.keys(call.symptoms_json).length > 0 && (
                                            <div>
                                                <p className="text-xs font-semibold text-slate-500 uppercase
                                      tracking-wide mb-1.5">Symptoms</p>
                                                <pre className="text-xs text-slate-400 bg-slate-950 rounded-lg p-4
                                        overflow-x-auto font-mono">
                                                    {JSON.stringify(call.symptoms_json, null, 2)}
                                                </pre>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
