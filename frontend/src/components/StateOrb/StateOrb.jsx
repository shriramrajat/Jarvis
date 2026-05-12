/**
 * JARVIS OS — State Orb
 * The pulsing central orb that visualizes current JARVIS state.
 * Different states = different colors, animations, and ring behaviors.
 */
import React, { useMemo } from 'react';
import './StateOrb.css';

const STATE_CONFIG = {
  IDLE: {
    color: '#00D4FF', label: 'IDLE', animation: 'orb-idle',
    message: 'Systems nominal. Awaiting input.',
  },
  LISTENING: {
    color: '#00FF9C', label: 'LISTENING', animation: 'orb-listening',
    message: 'Listening...',
  },
  THINKING: {
    color: '#F5A623', label: 'THINKING', animation: 'orb-thinking',
    message: 'Processing request...',
  },
  EXECUTING: {
    color: '#A855F7', label: 'EXECUTING', animation: 'orb-executing',
    message: 'Executing task...',
  },
  SPEAKING: {
    color: '#00D4FF', label: 'SPEAKING', animation: 'orb-listening',
    message: 'Responding...',
  },
  WAITING_CONFIRMATION: {
    color: '#F5A623', label: 'CONFIRM', animation: 'orb-thinking',
    message: 'Awaiting your confirmation.',
  },
  ERROR: {
    color: '#FF3B30', label: 'ERROR', animation: 'orb-error',
    message: 'An error occurred.',
  },
  INTERRUPTED: {
    color: '#F5A623', label: 'INTERRUPTED', animation: 'orb-thinking',
    message: 'Interrupted.',
  },
};

export default function StateOrb({ state = 'IDLE', mode = 'NORMAL' }) {
  const config = STATE_CONFIG[state] || STATE_CONFIG.IDLE;

  return (
    <div className="orb-container" id="state-orb">
      {/* Outer decorative rings */}
      <div className="orb-ring orb-ring--3" style={{ borderColor: `${config.color}18` }} />
      <div className="orb-ring orb-ring--2" style={{ borderColor: `${config.color}30` }} />
      <div className="orb-ring orb-ring--1" style={{ borderColor: `${config.color}55` }} />

      {/* Pulse ring (animated) */}
      {(state === 'LISTENING' || state === 'SPEAKING') && (
        <div className="orb-pulse-ring" style={{ borderColor: config.color }} />
      )}

      {/* Core orb */}
      <div
        className={`orb-core ${config.animation}`}
        style={{
          '--orb-color': config.color,
          background: `radial-gradient(circle at 35% 35%, ${config.color}CC, ${config.color}44 60%, transparent 100%)`,
          boxShadow: `0 0 30px ${config.color}66, 0 0 60px ${config.color}33, inset 0 0 20px ${config.color}22`,
          borderColor: `${config.color}88`,
        }}
      >
        {/* J logo */}
        <span className="orb-letter font-hud" style={{ color: config.color }}>J</span>
      </div>

      {/* State label below orb */}
      <div className="orb-info">
        <div className="orb-state font-hud uppercase" style={{ color: config.color }}>
          {config.label}
        </div>
        <div className="orb-message text-dim">
          {config.message}
        </div>
        <div className="orb-mode text-xs uppercase" style={{ color: `${config.color}88` }}>
          Mode: {mode}
        </div>
      </div>

      {/* Thinking progress dots */}
      {state === 'THINKING' && (
        <div className="orb-thinking-dots">
          <span className="dot" style={{ animationDelay: '0ms' }} />
          <span className="dot" style={{ animationDelay: '200ms' }} />
          <span className="dot" style={{ animationDelay: '400ms' }} />
        </div>
      )}
    </div>
  );
}
