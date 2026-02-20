import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

interface LayoutProps {
    onLogout: () => void;
}

export default function Layout({ onLogout }: LayoutProps) {
    return (
        <div className="min-h-screen flex">
            <Sidebar onLogout={onLogout} />
            <main className="flex-1 ml-60 min-h-screen bg-slate-950">
                <div className="max-w-7xl mx-auto px-6 py-8">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}
