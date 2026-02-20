/**
 * Toast — lightweight success / error notification.
 * Usage: <Toast message="..." type="success" onClose={() => …} />
 * Auto-dismisses after `duration` ms (default 3500).
 */
import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
    message: string;
    type?: ToastType;
    duration?: number;
    onClose: () => void;
}

export default function Toast({ message, type = 'success', duration = 3500, onClose }: ToastProps) {
    const [visible, setVisible] = useState(false);

    // Slide in
    useEffect(() => {
        const t1 = setTimeout(() => setVisible(true), 10);
        const t2 = setTimeout(() => { setVisible(false); setTimeout(onClose, 300); }, duration);
        return () => { clearTimeout(t1); clearTimeout(t2); };
    }, [duration, onClose]);

    const styles: Record<ToastType, string> = {
        success: 'bg-emerald-900/90 border-emerald-600/50 text-emerald-200',
        error: 'bg-red-900/90 border-red-600/50 text-red-200',
        info: 'bg-slate-800/90 border-slate-600/50 text-slate-200',
    };
    const icons: Record<ToastType, React.ReactNode> = {
        success: <CheckCircle size={17} className="text-emerald-400 shrink-0" />,
        error: <XCircle size={17} className="text-red-400 shrink-0" />,
        info: <CheckCircle size={17} className="text-slate-400 shrink-0" />,
    };

    return (
        <div
            className={`
        fixed bottom-6 right-6 z-[100] max-w-sm
        flex items-start gap-3 px-4 py-3.5
        rounded-xl border backdrop-blur-sm shadow-2xl
        transition-all duration-300
        ${styles[type]}
        ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
      `}
        >
            {icons[type]}
            <p className="text-sm flex-1 leading-snug">{message}</p>
            <button
                onClick={() => { setVisible(false); setTimeout(onClose, 300); }}
                className="shrink-0 opacity-50 hover:opacity-100 transition-opacity mt-0.5"
            >
                <X size={14} />
            </button>
        </div>
    );
}
