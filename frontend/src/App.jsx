/**
 * JARVIS OS — Main Application
 * Iron Man HUD Dashboard Layout:
 *
 * ┌─────────────────────────────────────────────┐
 * │              TITLE BAR                      │
 * ├──────────────┬──────────────┬───────────────┤
 * │              │  STATE ORB   │               │
 * │ CONVERSATION │   (center)   │    SYSTEM     │
 * │    PANEL     │              │    PANEL      │
 * │              │  COMMAND BAR │               │
 * └──────────────┴──────────────┴───────────────┘
 */
import React, { useState, useEffect } from 'react';
import './App.css';

import { useJarvisWS } from './hooks/useJarvisWS';
import TitleBar          from './components/TitleBar/TitleBar';
import StateOrb          from './components/StateOrb/StateOrb';
import CommandBar        from './components/CommandBar/CommandBar';
import ConversationPanel from './components/ConversationPanel/ConversationPanel';
import SystemPanel       from './components/SystemPanel/SystemPanel';

// Scan line overlay effect (ambient)
function ScanLine() {
  return <div className="scan-line" aria-hidden="true" />;
}

// Corner decorations
function CornerDecor() {
  return (
    <>
      <div className="corner corner--tl" />
      <div className="corner corner--tr" />
      <div className="corner corner--bl" />
      <div className="corner corner--br" />
    </>
  );
}

export default function App() {
  const {
    connected,
    jarvisState,
    jarvisMode,
    messages,
    context,
    sendCommand,
    send,
    respondToPermission,
  } = useJarvisWS();

  const [greeting] = useState(() => {
    const h = new Date().getHours();
    if (h < 12) return 'Good Morning';
    if (h < 17) return 'Good Afternoon';
    return 'Good Evening';
  });

  return (
    <div className="app" id="jarvis-app">
      <ScanLine />
      <CornerDecor />

      {/* ── Title Bar ─────────────────────────────── */}
      <TitleBar jarvisState={jarvisState} connected={connected} />

      {/* ── Main Layout ───────────────────────────── */}
      <div className="app__body">

        {/* Left — Conversation */}
        <aside className="app__left">
          <ConversationPanel messages={messages} respondToPermission={respondToPermission} />
        </aside>

        {/* Center — Orb + Command */}
        <main className="app__center">
          {/* Greeting */}
          <div className="app__greeting" id="greeting">
            <div className="app__greeting-text text-dim text-sm">{greeting}</div>
            <div className="app__greeting-name font-hud" style={{ color: 'var(--cyan)', fontSize: '22px', letterSpacing: '0.1em' }}>
              JARVIS OS
            </div>
          </div>

          {/* State Orb */}
          <StateOrb state={jarvisState} mode={jarvisMode} />

          {/* Quick action buttons */}
          <div className="app__quick-actions" id="quick-actions">
            {[
              { label: 'Focus Mode', key: 'focus', action: () => send('GUI_INPUT', { action: 'set_mode', value: 'FOCUS' }) },
              { label: 'Observe', key: 'observe', action: () => send('GUI_INPUT', { action: 'set_mode', value: 'OBSERVATION' }) },
              { label: 'Automate', key: 'automate', action: () => send('GUI_INPUT', { action: 'set_mode', value: 'AUTOMATION' }) },
            ].map(({ label, key, action }) => (
              <button
                key={key}
                className="btn app__quick-btn"
                id={`btn-${key}`}
                onClick={action}
                disabled={!connected}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Command Bar */}
          <div className="app__cmdbar-wrap">
            <CommandBar
              onSend={sendCommand}
              jarvisState={jarvisState}
              connected={connected}
            />
          </div>

          {/* Connection status (offline notice) */}
          {!connected && (
            <div className="app__offline" id="offline-notice">
              <span style={{ color: 'var(--red)' }}>●</span>
              <span className="text-xs text-dim">Backend offline — attempting to reconnect...</span>
            </div>
          )}
        </main>

        {/* Right — System Panel */}
        <aside className="app__right">
          <SystemPanel context={context} />
        </aside>
      </div>
    </div>
  );
}
