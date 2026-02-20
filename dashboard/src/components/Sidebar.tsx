import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard,
    PhoneCall,
    Users,
    AlertTriangle,
    HeartPulse,
    LogOut,
} from 'lucide-react';

const NAV_ITEMS = [
    { to: '/', icon: LayoutDashboard, label: 'Overview' },
    { to: '/calls', icon: PhoneCall, label: 'Calls' },
    { to: '/patients', icon: Users, label: 'Patients' },
    { to: '/alerts', icon: AlertTriangle, label: 'Red Alerts' },
];

interface SidebarProps {
    onLogout: () => void;
}

export default function Sidebar({ onLogout }: SidebarProps) {
    return (
        <aside className="fixed inset-y-0 left-0 w-60 flex flex-col bg-slate-900 border-r border-slate-800 z-20">
            {/* Logo */}
            <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-800">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700
                        flex items-center justify-center shadow-lg shadow-brand-500/20">
                    <HeartPulse size={20} className="text-white" />
                </div>
                <div>
                    <p className="font-bold text-white text-sm leading-tight">MatrAI</p>
                    <p className="text-xs text-slate-400">Admin Dashboard</p>
                </div>
            </div>

            {/* Nav */}
            <nav className="flex-1 px-3 py-4 space-y-1">
                {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={to === '/'}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
               transition-all duration-200 group
               ${isActive
                                ? 'bg-brand-500/15 text-brand-400 border border-brand-500/20'
                                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                            }`
                        }
                    >
                        <Icon size={17} />
                        {label}
                    </NavLink>
                ))}
            </nav>

            {/* Footer */}
            <div className="px-3 pb-4 border-t border-slate-800 pt-4">
                <button
                    onClick={onLogout}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm
                     font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/10
                     transition-all duration-200"
                >
                    <LogOut size={17} />
                    Sign out
                </button>
            </div>
        </aside>
    );
}
