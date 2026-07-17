'use client';
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import BottomNav from "../components/BottomNav";
import { LayoutDashboard, BarChart2, Cpu, Layers, MessageSquare, Settings, Database } from 'lucide-react';

export default function ClientLayout({ children }) {
  const pathname = usePathname();
  const isLogin = pathname === '/login';

  if (isLogin) {
    return <main className="login-wrapper">{children}</main>;
  }

  const [dialog, setDialog] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    const handleDialog = (e) => setDialog(e.detail);
    const handleToast = (e) => {
        setToast(e.detail);
        if (window.toastTimer) clearTimeout(window.toastTimer);
        window.toastTimer = setTimeout(() => setToast(null), e.detail.duration || 3000);
    };

    window.addEventListener('show-dialog', handleDialog);
    window.addEventListener('show-toast', handleToast);
    return () => {
        window.removeEventListener('show-dialog', handleDialog);
        window.removeEventListener('show-toast', handleToast);
    };
  }, []);

  return (
    <div className="dashboard-layout animate-fade-in">
      <aside className="sidebar desktop-only">
        <div className="sidebar-header" style={{ padding: '0 16px' }}>
          <h1 className="gradient-text" style={{ fontSize: '1.8rem', fontWeight: '700', marginBottom: '4px' }}>NEXUS</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Smart Home Platform</p>
        </div>
        
        <nav className="nav-menu" style={{ overflowY: 'auto', flex: 1, gap: '8px', paddingRight: '8px' }}>
          <div style={{ padding: '16px 16px 8px', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase', opacity: 0.6 }}>Command Center</div>
          <Link href="/" className={`nav-item text-base ${pathname === '/' ? 'active' : ''}`}>
            <LayoutDashboard size={18} />
            Dashboard
          </Link>
          <Link href="/analytics" className={`nav-item text-base ${pathname === '/analytics' ? 'active' : ''}`}>
            <BarChart2 size={18} />
            Analytics
          </Link>

          <div style={{ padding: '24px 16px 8px', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase', opacity: 0.6 }}>Devices & Config</div>
          <Link href="/devices" className={`nav-item text-base ${pathname === '/devices' ? 'active' : ''}`}>
            <Cpu size={18} />
            Edit Devices
          </Link>
          <Link href="/scenes" className={`nav-item text-base ${pathname === '/scenes' ? 'active' : ''}`}>
            <Layers size={18} />
            Scenes
          </Link>

          <div style={{ padding: '24px 16px 8px', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase', opacity: 0.6 }}>System</div>
          <Link href="/messages" className={`nav-item text-base ${pathname === '/messages' ? 'active' : ''}`}>
            <MessageSquare size={18} />
            AI Assistant
          </Link>
          <Link href="/settings" className={`nav-item text-base ${pathname === '/settings' ? 'active' : ''}`}>
            <Settings size={18} />
            Settings & System
          </Link>
          <Link href="/database" className={`nav-item text-base ${pathname === '/database' ? 'active' : ''}`}>
            <Database size={18} />
            Database Admin
          </Link>
        </nav>

        <div className="glass-panel" style={{ margin: '12px 16px', padding: '12px' }}>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>ZALO BOT</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#10b981' }}></div>
            <span style={{ fontSize: '0.8rem', fontWeight: '500' }}>Active (Ngrok)</span>
          </div>
        </div>
      </aside>
      
      <main className="main-content">
        {children}
      </main>

      <div className="mobile-only">
        <BottomNav />
      </div>

      {/* Global Dialog */}
      {dialog && (
        <div className="dialog-overlay z-[9999]">
          <div className="dialog-content text-center max-w-sm w-full mx-4">
            <h3 className={`text-xl font-semibold mb-2 ${dialog.type === 'danger' ? 'text-[var(--danger)]' : dialog.type === 'warning' ? 'text-[var(--warning)]' : 'text-[var(--text-primary)]'}`}>
              {dialog.title}
            </h3>
            <p className="text-[var(--text-secondary)] mb-6 text-sm">{dialog.message}</p>
            <div className="flex justify-center gap-3 mt-4">
              {dialog.onConfirm ? (
                <>
                  <button onClick={() => setDialog(null)} className="btn-secondary flex-1 py-2">Cancel</button>
                  <button 
                    onClick={() => { dialog.onConfirm(); setDialog(null); }} 
                    className={`btn-primary flex-1 py-2 ${dialog.type === 'danger' ? 'bg-[var(--danger)] hover:bg-red-600 border-transparent' : ''}`}
                  >
                    Confirm
                  </button>
                </>
              ) : (
                <button onClick={() => setDialog(null)} className="btn-primary flex-1 py-2">OK</button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Global Toast */}
      {toast && (
        <div className={`toast toast-${toast.type} z-[9999] top-6 left-1/2 -translate-x-1/2 shadow-2xl`}>
          {toast.type === 'success' ? '✅' : toast.type === 'danger' ? '❌' : toast.type === 'warning' ? '⚠️' : 'ℹ️'} {toast.message}
        </div>
      )}

    </div>
  );
}
