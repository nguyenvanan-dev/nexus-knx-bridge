'use client';

import { useState } from 'react';
import styles from './page.module.css';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      if (res.ok) {
        window.location.href = '/';
      } else {
        const data = await res.json();
        setError(data.error || 'Login failed');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  return (
    <div className={styles.splitContainer}>
      {/* Left Side: Branding / Abstract Gradient (Hidden on Mobile) */}
      <div className={`${styles.brandSection} desktop-only`}>
        <div className={styles.brandOverlay}>
          <div className={styles.brandContent}>
            <h1 className="gradient-text" style={{ fontSize: '3rem', fontWeight: '800' }}>NEXUS</h1>
            <p style={{ fontSize: '1.2rem', color: 'rgba(255,255,255,0.8)' }}>
              Intelligent Smart Home Command Center
            </p>
          </div>
        </div>
      </div>
      
      {/* Right Side: Login Form */}
      <div className={styles.formSection}>
        <div className={styles.loginBox}>
          <div className={styles.logo}>
            <h2 className="gradient-text">Welcome Back</h2>
          </div>
          
          <form onSubmit={handleLogin}>
            {error && <div className={styles.error}>{error}</div>}
            
            <div className={styles.inputGroup}>
              <label>Username</label>
              <input
                type="text"
                placeholder="admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            
            <div className={styles.inputGroup}>
              <label>Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            
            <button type="submit" className={styles.submitBtn}>
              Sign In
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
