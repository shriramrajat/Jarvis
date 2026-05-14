import React from 'react';
import './StateOrb.css';

export default function StateOrb({ state, mode }) {
  // state can be: IDLE, LISTENING, THINKING, SPEAKING, EXECUTING
  return (
    <div className="state-orb-container">
      <div className={`state-orb state-orb--${state.toLowerCase()}`}>
        <div className="state-orb__core" />
        <div className="state-orb__ring state-orb__ring-1" />
        <div className="state-orb__ring state-orb__ring-2" />
        <div className="state-orb__ring state-orb__ring-3" />
      </div>
      <div className="state-orb-label font-hud">
        {state} <span className="text-dim text-xs">| {mode}</span>
      </div>
    </div>
  );
}