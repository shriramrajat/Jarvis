import React from 'react';
import './TitleBar.css';

export default function TitleBar({ jarvisState, connected }) {
  const closeApp = () => {
    if (window.electron) window.electron.close();
  };

  const minimizeApp = () => {
    if (window.electron) window.electron.minimize();
  };

  return (
    <div className="titlebar">
      <div className="titlebar__logo font-hud">
        <span className="text-cyan">JARVIS</span>
        <span className="text-dim text-xs ml-2">v0.1</span>
      </div>
      
      <div className="titlebar__status">
        <div className={`status-dot ${connected ? 'status-dot--online' : 'status-dot--offline'}`} />
        <span className="text-xs text-dim">
          {connected ? 'UPLINK ACTIVE' : 'NO SIGNAL'}
        </span>
      </div>

      <div className="titlebar__controls">
        <button className="titlebar__btn" onClick={minimizeApp}>_</button>
        <button className="titlebar__btn titlebar__btn--close" onClick={closeApp}>✕</button>
      </div>
    </div>
  );
}