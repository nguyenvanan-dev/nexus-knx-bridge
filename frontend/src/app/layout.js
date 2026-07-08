import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";


const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "Nexus Command Center",
  description: "Smart Home Admin Dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <div className="dashboard-layout animate-fade-in">
          <aside className="sidebar">
            <div style={{ padding: '0 16px' }}>
              <h1 className="gradient-text" style={{ fontSize: '1.8rem', fontWeight: '700', marginBottom: '4px' }}>NEXUS</h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Smart Home Platform v3.1</p>
            </div>
            
            <nav className="nav-menu" style={{ overflowY: 'auto', flex: 1 }}>
              {/* Overview */}
              <div style={{ padding: '8px 12px 4px', fontSize: '0.65rem', fontWeight: '700', color: '#4B5563', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Overview</div>
              <Link href="/" className="nav-item">
                <span>📊</span> Dashboard
              </Link>
              <Link href="/floorplan" className="nav-item">
                <span>🏠</span> Digital Twin
              </Link>
              <Link href="/analytics" className="nav-item">
                <span>📈</span> Analytics
              </Link>

              {/* Control */}
              <div style={{ padding: '12px 12px 4px', fontSize: '0.65rem', fontWeight: '700', color: '#4B5563', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Control</div>
              <Link href="/devices" className="nav-item">
                <span>🔌</span> Devices
              </Link>
              <Link href="/scenes" className="nav-item">
                <span>🎬</span> Scenes
              </Link>
              <Link href="/automation2" className="nav-item">
                <span>⚡</span> Automation
              </Link>

              {/* AI & Chat */}
              <div style={{ padding: '12px 12px 4px', fontSize: '0.65rem', fontWeight: '700', color: '#4B5563', letterSpacing: '0.1em', textTransform: 'uppercase' }}>AI & Chat</div>
              <Link href="/messages" className="nav-item">
                <span>💬</span> AI Assistant
              </Link>

              {/* Tools */}
              <div style={{ padding: '12px 12px 4px', fontSize: '0.65rem', fontWeight: '700', color: '#4B5563', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Tools</div>
              <Link href="/health" className="nav-item">
                <span>🏥</span> Health Monitor
              </Link>
              <Link href="/diagnostics" className="nav-item">
                <span>🛠️</span> Diagnostics Hub
              </Link>
              <Link href="/events" className="nav-item">
                <span>🔔</span> Event Center
              </Link>
              <Link href="/database" className="nav-item">
                <span>🗄️</span> Database
              </Link>
              <Link href="/settings" className="nav-item">
                <span>⚙️</span> Settings
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
        </div>
      </body>
    </html>
  );
}
