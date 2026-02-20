/**
 * CallDetailModal — full call detail view with:
 *   - Risk badge, phone, timestamp
 *   - AI advice
 *   - Structured symptoms display
 *   - Full scrollable transcript
 *   - "Notify ASHA Worker" button (mock SMS for hackathon)
 */
import { useState, useEffect, useCallback } from 'react';
import {
    X, Phone, Clock, AlertTriangle, FileText,
    Stethoscope, Bell, CheckCircle,
} from 'lucide-react';
import { type Call } from '../lib/supabase';
import RiskBadge from './RiskBadge';
import Toast from './Toast';

interface CallDetailModalProps {
    call: Call;
    onClose: () => void;
}

export default function CallDetailModal({ call, onClose }: CallDetailModalProps) {
    const [toastMsg, setToastMsg] = useState<string | null>(null);
    const [notified, setNotified] = useState(false);

    // Close on Escape key
    const handleKey = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    }, [onClose]);

    useEffect(() => {
        document.addEventListener('keydown', handleKey);
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', handleKey);
            document.body.style.overflow = '';
        };
    }, [handleKey]);

    // -----------------------------------------------------------------------
    // Parse symptoms_json into human-readable key-value entries
    // -----------------------------------------------------------------------
    const symptoms = call.symptoms_json ?? {};
    const symptomEntries = Object.entries(symptoms);

    // Extract clinical_reason if present (may be nested inside symptoms or top-level)
    const clinicalReason: string =
        (symptoms.clinical_reason as string) ||
        (symptoms.reason as string) ||
        (symptoms.triage_reason as string) ||
        '';

    // -----------------------------------------------------------------------
    // Mock ASHA notification
    // -----------------------------------------------------------------------
    const handleNotifyAsha = () => {
        const phone = call.users?.phone ?? 'Unknown';
        const risk = call.risk_level ?? 'Unknown';
        const reason = clinicalReason || call.ai_advice?.slice(0, 80) || 'High risk detected';
        const message = `[MOCK SMS]: Alerting ASHA for Patient at ${phone} – High Risk: ${reason}`;

        console.log(message);
        setNotified(true);
        setToastMsg(`ASHA Worker notified for ${phone}`);
    };

    // -----------------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------------
    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm
                   flex items-center justify-center p-4"
                onClick={e => { if (e.target === e.currentTarget) onClose(); }}
            >
                {/* Panel */}
                <div
                    className="relative w-full max-w-2xl max-h-[90vh] flex flex-col
                     bg-slate-900 rounded-2xl border border-slate-700/60
                     shadow-2xl shadow-black/60 overflow-hidden
                     animate-[slideUp_0.2s_ease-out]"
                >
                    {/* ---- Header ---- */}
                    <div className="flex items-start justify-between px-6 py-5
                          border-b border-slate-800 shrink-0">
                        <div className="space-y-1.5">
                            <div className="flex items-center gap-2.5">
                                <RiskBadge level={call.risk_level} />
                                <span className="text-slate-500 text-xs">Call Detail</span>
                            </div>
                            <div className="flex items-center gap-2 text-white">
                                <Phone size={14} className="text-slate-400" />
                                <span className="font-semibold text-lg">
                                    {call.users?.phone ?? 'Unknown caller'}
                                </span>
                                {call.users?.language && (
                                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800
                                   text-slate-400 border border-slate-700 uppercase">
                                        {call.users.language}
                                    </span>
                                )}
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-slate-500">
                                <Clock size={12} />
                                {new Date(call.created_at).toLocaleString('en-IN', {
                                    weekday: 'short', day: '2-digit', month: 'short',
                                    year: 'numeric', hour: '2-digit', minute: '2-digit',
                                })}
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 rounded-lg text-slate-500 hover:text-white
                         hover:bg-slate-800 transition-colors"
                        >
                            <X size={18} />
                        </button>
                    </div>

                    {/* ---- Scrollable body ---- */}
                    <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">

                        {/* AI Advice */}
                        {call.ai_advice && (
                            <section>
                                <h3 className="flex items-center gap-2 text-xs font-semibold
                               text-slate-500 uppercase tracking-widest mb-3">
                                    <Stethoscope size={13} />
                                    AI Advice
                                </h3>
                                <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/40">
                                    <p className="text-sm text-slate-200 leading-relaxed">
                                        {call.ai_advice}
                                    </p>
                                </div>
                            </section>
                        )}

                        {/* Clinical Reason (from triage engine) */}
                        {clinicalReason && (
                            <section>
                                <h3 className="flex items-center gap-2 text-xs font-semibold
                               text-slate-500 uppercase tracking-widest mb-3">
                                    <AlertTriangle size={13} className="text-amber-400" />
                                    Clinical Reason (Triage Engine)
                                </h3>
                                <div className="bg-amber-500/5 rounded-xl p-4
                                border border-amber-500/20">
                                    <p className="text-sm text-amber-200 leading-relaxed">
                                        {clinicalReason}
                                    </p>
                                </div>
                            </section>
                        )}

                        {/* Symptoms */}
                        {symptomEntries.length > 0 && (
                            <section>
                                <h3 className="flex items-center gap-2 text-xs font-semibold
                               text-slate-500 uppercase tracking-widest mb-3">
                                    <FileText size={13} />
                                    Collected Symptoms
                                </h3>
                                <div className="grid grid-cols-2 gap-2">
                                    {symptomEntries
                                        .filter(([k]) => !['clinical_reason', 'reason', 'triage_reason'].includes(k))
                                        .map(([key, val]) => (
                                            <div key={key}
                                                className="bg-slate-800/50 rounded-lg px-3 py-2.5
                                      border border-slate-700/30">
                                                <p className="text-xs text-slate-500 capitalize mb-0.5">
                                                    {key.replace(/_/g, ' ')}
                                                </p>
                                                <p className="text-sm text-slate-200 font-medium">
                                                    {String(val)}
                                                </p>
                                            </div>
                                        ))}
                                </div>
                                {/* Raw JSON fallback */}
                                <details className="mt-2">
                                    <summary className="text-xs text-slate-600 cursor-pointer
                                      hover:text-slate-400 transition-colors list-none">
                                        <span className="border border-slate-800 rounded px-2 py-0.5
                                     hover:border-slate-600">View raw JSON</span>
                                    </summary>
                                    <pre className="mt-2 text-xs text-slate-500 bg-slate-950 rounded-lg
                                  p-3 overflow-x-auto font-mono">
                                        {JSON.stringify(symptoms, null, 2)}
                                    </pre>
                                </details>
                            </section>
                        )}

                        {/* Transcript */}
                        {call.transcript && (
                            <section>
                                <h3 className="flex items-center gap-2 text-xs font-semibold
                               text-slate-500 uppercase tracking-widest mb-3">
                                    <FileText size={13} />
                                    Full Transcript
                                </h3>
                                <pre className="text-xs text-slate-400 bg-slate-950 rounded-xl
                                p-4 overflow-y-auto max-h-64 whitespace-pre-wrap
                                font-mono leading-relaxed border border-slate-800">
                                    {call.transcript}
                                </pre>
                            </section>
                        )}
                    </div>

                    {/* ---- Footer / Actions ---- */}
                    <div className="shrink-0 flex items-center justify-between
                          px-6 py-4 border-t border-slate-800 bg-slate-900/80">
                        <button
                            onClick={onClose}
                            className="text-sm text-slate-400 hover:text-white transition-colors"
                        >
                            Close
                        </button>

                        {/* Only show ASHA button for RED / YELLOW */}
                        {(call.risk_level === 'RED' || call.risk_level === 'YELLOW') && (
                            <button
                                onClick={handleNotifyAsha}
                                disabled={notified}
                                className={`
                  flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold
                  transition-all duration-200 focus:outline-none
                  ${notified
                                        ? 'bg-emerald-800/40 text-emerald-400 border border-emerald-700/40 cursor-default'
                                        : call.risk_level === 'RED'
                                            ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-500/25'
                                            : 'bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-500/25'
                                    }
                `}
                            >
                                {notified
                                    ? <><CheckCircle size={15} /> ASHA Notified</>
                                    : <><Bell size={15} /> Notify ASHA Worker</>
                                }
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Toast */}
            {toastMsg && (
                <Toast
                    message={toastMsg}
                    type="success"
                    onClose={() => setToastMsg(null)}
                />
            )}

            {/* Slide-up keyframe (injected inline so no Tailwind config needed) */}
            <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(16px) scale(0.98); }
          to   { opacity: 1; transform: translateY(0)    scale(1);    }
        }
      `}</style>
        </>
    );
}
