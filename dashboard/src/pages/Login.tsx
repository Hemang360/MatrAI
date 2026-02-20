import { useState, type FormEvent } from 'react';
import { HeartPulse, Lock, Eye, EyeOff } from 'lucide-react';

// Hardcoded password for hackathon — swap for Supabase Auth in production
const ADMIN_PASSWORD = import.meta.env.VITE_ADMIN_PASSWORD || 'matrai2025';

interface LoginProps {
    onLogin: () => void;
}

export default function Login({ onLogin }: LoginProps) {
    const [password, setPassword] = useState('');
    const [showPass, setShowPass] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        // Simulate a slight delay for UX
        await new Promise(r => setTimeout(r, 500));

        if (password === ADMIN_PASSWORD) {
            sessionStorage.setItem('matrai_auth', 'true');
            onLogin();
        } else {
            setError('Incorrect password. Please try again.');
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
            {/* Background glow */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                        w-[600px] h-[600px] bg-brand-600/10 rounded-full blur-3xl" />
            </div>

            <div className="relative w-full max-w-md">
                {/* Card */}
                <div className="glass rounded-2xl p-8 shadow-2xl shadow-black/40">
                    {/* Logo */}
                    <div className="flex flex-col items-center mb-8">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-400 to-brand-700
                            flex items-center justify-center shadow-xl shadow-brand-500/30 mb-4">
                            <HeartPulse size={32} className="text-white" />
                        </div>
                        <h1 className="text-2xl font-bold text-white">MatrAI Admin</h1>
                        <p className="text-slate-400 text-sm mt-1">Doctor & ASHA Worker Dashboard</p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                Admin Password
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                                    <Lock size={16} className="text-slate-500" />
                                </div>
                                <input
                                    type={showPass ? 'text' : 'password'}
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="Enter password"
                                    className="input pl-9 pr-10"
                                    autoFocus
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPass(!showPass)}
                                    className="absolute inset-y-0 right-3 flex items-center text-slate-500
                             hover:text-slate-300 transition-colors"
                                >
                                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 text-red-400 text-sm
                              bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                                <span>{error}</span>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading || !password}
                            className="btn-primary w-full flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <span className="w-4 h-4 border-2 border-white/30 border-t-white
                                 rounded-full animate-spin" />
                            ) : 'Sign in'}
                        </button>
                    </form>
                </div>

                <p className="text-center text-slate-600 text-xs mt-6">
                    MatrAI · Maternal AI Health Platform
                </p>
            </div>
        </div>
    );
}
