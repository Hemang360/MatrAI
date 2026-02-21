import { useEffect, useState, useMemo } from 'react';
import { Users, CheckCircle, XCircle, Search } from 'lucide-react';
import { fetchUsers, type User } from '../lib/supabase';

export default function PatientsPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchUsers(100)
            .then(r => setUsers(r.data ?? []))
            .finally(() => setLoading(false));
    }, []);

    const filtered = useMemo(() => {
        const q = search.toLowerCase();
        return users.filter(u => u.phone.includes(q));
    }, [search, users]);


    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Patients</h1>
                    <p className="text-slate-400 text-sm mt-1">
                        Registered callers and consent status
                    </p>
                </div>
                <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Search by phone…"
                        className="input pl-9 w-56"
                    />
                </div>
            </div>

            <div className="glass rounded-xl overflow-hidden">
                <div className="grid grid-cols-12 gap-4 px-5 py-3 border-b border-slate-700/50
                        text-xs font-medium text-slate-500 uppercase tracking-wide">
                    <div className="col-span-1">#</div>
                    <div className="col-span-4">Phone</div>
                    <div className="col-span-2">Language</div>
                    <div className="col-span-3">Consent</div>
                    <div className="col-span-2">Registered</div>
                </div>

                {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="px-5 py-4 animate-pulse border-b border-slate-800">
                            <div className="h-4 bg-slate-800 rounded w-full" />
                        </div>
                    ))
                ) : filtered.length === 0 ? (
                    <div className="px-5 py-12 text-center">
                        <Users size={40} className="text-slate-700 mx-auto mb-3" />
                        <p className="text-slate-500">No patients registered yet.</p>
                    </div>
                ) : (
                    filtered.map((user, idx) => (
                        <div
                            key={user.id}
                            className="grid grid-cols-12 gap-4 px-5 py-4 border-b border-slate-800/60
                         last:border-0 glass-hover transition-colors text-sm"
                        >
                            <div className="col-span-1 text-slate-500">{idx + 1}</div>
                            <div className="col-span-4 font-medium text-white">{user.phone}</div>
                            <div className="col-span-2 text-slate-400 uppercase text-xs font-medium">
                                {user.language}
                            </div>
                            <div className="col-span-3">
                                {user.consent_given ? (
                                    <span className="badge-green">
                                        <CheckCircle size={11} /> Consented
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full
                                   text-xs font-medium bg-slate-700/50 text-slate-400
                                   border border-slate-600/30">
                                        <XCircle size={11} /> Not yet
                                    </span>
                                )}
                            </div>
                            <div className="col-span-2 text-slate-500 text-xs">
                                {new Date(user.created_at).toLocaleDateString('en-IN', {
                                    day: '2-digit', month: 'short', year: 'numeric'
                                })}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
