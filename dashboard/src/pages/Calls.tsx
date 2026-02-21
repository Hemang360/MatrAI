import { useState } from 'react';
import { Search } from 'lucide-react';
import CallLog from '../components/CallLog';

export default function CallsPage() {
    const [search, setSearch] = useState('');

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Calls</h1>
                    <p className="text-slate-400 text-sm mt-1">
                        Real-time call log — RED alerts pin to the top automatically
                    </p>
                </div>
                <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Filter by phone or risk…"
                        className="input pl-9 w-64"
                    />
                </div>
            </div>

            <CallLog limit={100} search={search} />
        </div>
    );
}
