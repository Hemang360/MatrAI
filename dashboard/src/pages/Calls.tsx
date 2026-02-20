import { useEffect, useState } from 'react';
import { Search, ChevronDown, ChevronUp } from 'lucide-react';
import { fetchRecentCalls, type Call } from '../lib/supabase';
import RiskBadge from '../components/RiskBadge';

export default function CallsPage() {
    const [calls, setCalls] = useState<Call[]>([]);
    const [filtered, setFiltered] = useState<Call[]>([]);
    const [search, setSearch] = useState('');
    const [expanded, setExpanded] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchRecentCalls(100)
            .then(r => { setCalls(r.data ?? []); setFiltered(r.data ?? []); })
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        const q = search.toLowerCase();
        setFiltered(
            calls.filter(c =>
                (c.users?.phone ?? '').includes(q) ||
                (c.risk_level ?? '').toLowerCase().includes(q) ||
                (c.ai_advice ?? '').toLowerCase().includes(q)
            )
        );
    }, [search, calls]);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Calls</h1>
                    <p className="text-slate-400 text-sm mt-1">
                        Full call log with transcripts and triage outcomes
                    </p>
                </div>
                <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Search calls…"
                        className="input pl-9 w-56"
                    />
                </div>
            </div>

            <div className="glass rounded-xl overflow-hidden">
                {/* Table header */}
                <div className="grid grid-cols-12 gap-4 px-5 py-3 border-b border-slate-700/50
                        text-xs font-medium text-slate-500 uppercase tracking-wide">
                    <div className="col-span-1">#</div>
                    <div className="col-span-3">Phone</div>
                    <div className="col-span-2">Risk</div>
                    <div className="col-span-4">Advice (preview)</div>
                    <div className="col-span-2">Date</div>
                </div>

                {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="px-5 py-4 animate-pulse border-b border-slate-800">
                            <div className="h-4 bg-slate-800 rounded w-full" />
                        </div>
                    ))
                ) : filtered.length === 0 ? (
                    <div className="px-5 py-12 text-center text-slate-500">
                        {search ? 'No calls match your search.' : 'No calls yet.'}
                    </div>
                ) : (
                    filtered.map((call, idx) => (
                        <div key={call.id} className="border-b border-slate-800/60 last:border-0">
                            {/* Row */}
                            <button
                                onClick={() => setExpanded(expanded === call.id ? null : call.id)}
                                className="w-full grid grid-cols-12 gap-4 px-5 py-4 text-left
                           glass-hover transition-colors"
                            >
                                <div className="col-span-1 text-slate-500 text-sm">{idx + 1}</div>
                                <div className="col-span-3 text-sm font-medium text-white">
                                    {call.users?.phone ?? '—'}
                                </div>
                                <div className="col-span-2">
                                    <RiskBadge level={call.risk_level} />
                                </div>
                                <div className="col-span-4 text-sm text-slate-400 truncate">
                                    {call.ai_advice?.slice(0, 60) ?? '—'}
                                </div>
                                <div className="col-span-2 flex items-center justify-between">
                                    <span className="text-xs text-slate-500">
                                        {new Date(call.created_at).toLocaleDateString('en-IN')}
                                    </span>
                                    {expanded === call.id
                                        ? <ChevronUp size={14} className="text-slate-500" />
                                        : <ChevronDown size={14} className="text-slate-500" />}
                                </div>
                            </button>

                            {/* Expanded transcript + advice */}
                            {expanded === call.id && (
                                <div className="px-5 pb-5 space-y-4 bg-slate-900/40">
                                    {call.ai_advice && (
                                        <div>
                                            <p className="text-xs font-semibold text-slate-500 uppercase
                                    tracking-wide mb-2">AI Advice</p>
                                            <p className="text-sm text-slate-300 leading-relaxed">
                                                {call.ai_advice}
                                            </p>
                                        </div>
                                    )}
                                    {call.transcript && (
                                        <div>
                                            <p className="text-xs font-semibold text-slate-500 uppercase
                                    tracking-wide mb-2">Transcript</p>
                                            <pre className="text-xs text-slate-400 bg-slate-900 rounded-lg p-4
                                      overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                                                {call.transcript}
                                            </pre>
                                        </div>
                                    )}
                                    {call.symptoms_json && Object.keys(call.symptoms_json).length > 0 && (
                                        <div>
                                            <p className="text-xs font-semibold text-slate-500 uppercase
                                    tracking-wide mb-2">Symptoms</p>
                                            <pre className="text-xs text-slate-400 bg-slate-900 rounded-lg p-4
                                      overflow-x-auto font-mono">
                                                {JSON.stringify(call.symptoms_json, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
