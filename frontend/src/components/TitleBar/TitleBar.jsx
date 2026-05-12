/**
 * JARVIS OS — Title Bar
 * Custom frameless window controls: drag region + minimize/maximize/close.
 */
import React, { useState, useEffect } from 'react';
import './TitleBar.css';

export default function TitleBar({ jarvisState, connected }) {
  const [isMaximized, setIsMaximized] = useState(false);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleMaximize = async () => {
    await window.jarvis?.maximize();
    setIsMaximized(await window.jarvis?.isMaximized());
  };

  const stateColor = {
    IDLE:                 'var(--cyan)',
    LISTENING:            'var(--green)',
    THINKING:             'var(--amber)',
    EXECUTING:            'var(--purple)',
    SPEAKING:             'var(--cyan)',
    WAITING_CONFIRMATION: 'var(--amber)',
    ERROR:                'var(--red)',
    INTERRUPTED:          'var(--amber)',
  }[jarvisState] || 'var(--text-dim)';

  return (
    <div className="titlebar" id="titlebar">
      {/* Drag region */}
      <div className="titlebar__drag" />

      {/* Left — Logo */}
      <div className="titlebar__left">
        <div className="titlebar__logo">
          <span className="titlebar__logo-j font-hud">J</span>
        </div>
        <span className="titlebar__name font-hud uppercase">JARVIS OS</span>
        <span className="titlebar__version text-dim text-xs">v0.1.0</span>
      </div>

      {/* Center — State + Connection */}
      <div className="titlebar__center">
        <div className="titlebar__state-dot" style={{ background: stateColor, boxShadow: `0 0 8px ${stateColor}` }} />
        <span className="titlebar__state font-hud text-xs uppercase" style={{ color: stateColor }}>
          {jarvisState}
        </span>
        <div className={`titlebar__conn ${connected ? 'titlebar__conn--on' : 'titlebar__conn--off'}`}>
          {connected ? '● ONLINE' : '○ OFFLINE'}
        </div>
      </div>

      {/* Right — Clock + Window Controls */}
      <div className="titlebar__right">
        <span className="titlebar__time font-hud text-xs text-dim">
          {time.toLocaleTimeString('en-US', { hour12: false })}
        </span>
        <div className="titlebar__controls">
          <button
            className="titlebar__btn titlebar__btn--min"
            id="btn-minimize"
            onClick={() => window.jarvis?.minimize()}
            title="Minimize"
          >─</button>
          <button
            className="titlebar__btn titlebar__btn--max"
            id="btn-maximize"
            onClick={handleMaximize}
            title={isMaximized ? 'Restore' : 'Maximize'}
          >{isMaximized ? '❐' : '□'}</button>
          <button
            className="titlebar__btn titlebar__btn--close"
            id="btn-close"
            onClick={() => window.jarvis?.close()}
            title="Minimize to tray"
          >✕</button>
        </div>
      </div>
    </div>
  );
}
