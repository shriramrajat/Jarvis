import React from 'react';
import './StateOrb.css';

export default function StateOrb({ state, mode }) {
  // state can be: IDLE, LISTENING, THINKING, SPEAKING, EXECUTING
  const lowerState = (state || 'IDLE').toLowerCase();
  
  return (
    <div className="orb-container">
      <div className={`arc-reactor arc-reactor--${lowerState}`}>
        {/* Hardware accelerated spinning rings */}
        <div className="arc-ring arc-ring-1" />
        <div className="arc-ring arc-ring-2" />
        <div className="arc-ring arc-ring-3" />
        
        {/* Core SVG hexagon grid and glow */}
        <div className="arc-core">
          <svg viewBox="0 0 100 100" className="arc-core-svg">
            <polygon points="50,5 95,25 95,75 50,95 5,75 5,25" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.3" />
            <circle cx="50" cy="50" r="25" fill="currentColor" opacity="0.8" />
          </svg>
        </div>

        {/* CSS-based pulse (using opacity/transform scale instead of box-shadow) */}
        {['listening', 'speaking'].includes(lowerState) && (
          <div className="arc-pulse" />
        )}
      </div>

      <div className="orb-info font-hud">
        <div className="orb-state" style={{ color: lowerState === 'thinking' ? 'var(--amber)' : 'var(--cyan)' }}>
          {state}
        </div>
        <div className="orb-mode text-dim">{mode || 'NORMAL'} MODE</div>
      </div>
    </div>
  );
}