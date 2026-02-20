import { type RiskLevel } from '../lib/supabase';
import { AlertTriangle, CheckCircle, AlertCircle, HelpCircle } from 'lucide-react';

interface RiskBadgeProps {
    level: RiskLevel | null;
}

export default function RiskBadge({ level }: RiskBadgeProps) {
    if (!level) {
        return (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full
                        text-xs font-medium bg-slate-700/50 text-slate-400 border border-slate-600/30">
                <HelpCircle size={11} />
                Unknown
            </span>
        );
    }

    const map = {
        RED: { cls: 'badge-red', icon: AlertTriangle, label: 'RED' },
        YELLOW: { cls: 'badge-yellow', icon: AlertCircle, label: 'YELLOW' },
        GREEN: { cls: 'badge-green', icon: CheckCircle, label: 'GREEN' },
    };

    const { cls, icon: Icon, label } = map[level];
    return (
        <span className={cls}>
            <Icon size={11} />
            {label}
        </span>
    );
}
