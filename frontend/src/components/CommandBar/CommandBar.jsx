/**
 * JARVIS OS — Command Bar
 * The global text input for sending commands to JARVIS.
 * Always accessible, voice-first but text always available.
 */
import React, { useState, useRef, useEffect } from 'react';
import './CommandBar.css';

export default function CommandBar({ onSend, jarvisState, connected }) {
  const [input, setInput] = useState('');
  const inputRef = useRef(null);
  const isProcessing = ['THINKING', 'EXECUTING', 'SPEAKING'].includes(jarvisState);

  // Focus on mount
  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isProcessing || !connected) return;
    onSend(text);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e);
    }
  };

  const placeholders = [
    'Type a command or ask anything...',
    'Open VS Code...',
    'What\'s my CPU usage?',
    'Search for project files...',
    'Set a reminder for 3 PM...',
  ];

  const [placeholderIdx] = useState(() => Math.floor(Math.random() * placeholders.length));

  return (
    <form className="cmdbar" id="command-bar" onSubmit={handleSubmit}>
      {/* Icon */}
      <div className="cmdbar__icon">
        {isProcessing ? (
          <div className="cmdbar__spinner" />
        ) : (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M6.5 1a5.5 5.5 0 1 0 3.603 9.697l3.35 3.35a.75.75 0 1 0 1.06-1.061l-3.35-3.35A5.5 5.5 0 0 0 6.5 1z"
              fill="currentColor" opacity=".5" />
            <path d="M6.5 3a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7z" fill="currentColor" />
          </svg>
        )}
      </div>

      {/* Input */}
      <input
        ref={inputRef}
        className="cmdbar__input"
        id="jarvis-command-input"
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={isProcessing ? 'Processing...' : placeholders[placeholderIdx]}
        disabled={isProcessing || !connected}
        autoComplete="off"
        spellCheck="false"
      />

      {/* Waveform decoration (idle) */}
      {!isProcessing && (
        <div className="cmdbar__wave">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="cmdbar__wave-bar" style={{ animationDelay: `${i * 80}ms` }} />
          ))}
        </div>
      )}

      {/* Send button */}
      <button
        type="submit"
        className="cmdbar__send btn btn-primary"
        id="btn-send-command"
        disabled={!input.trim() || isProcessing || !connected}
      >
        {isProcessing ? '...' : '↵'}
      </button>
    </form>
  );
}
