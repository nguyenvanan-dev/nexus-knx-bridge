import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Lightbulb, Grid, Bot, Settings } from 'lucide-react';

export default function BottomNav() {
  const pathname = usePathname();

  const navItems = [
    { href: '/', icon: Home, label: 'Home' },
    { href: '/devices', icon: Lightbulb, label: 'Devices' },
    { href: '/floorplan', icon: Grid, label: 'Rooms' },
    { href: '/messages', icon: Bot, label: 'AI' },
    { href: '/settings', icon: Settings, label: 'Settings' }
  ];

  return (
    <nav className="bottom-nav">
      {navItems.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link key={item.href} href={item.href} className={`bottom-nav-item ${isActive ? 'active' : ''}`}>
            <item.icon size={24} />
            <span className="bottom-nav-label">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
