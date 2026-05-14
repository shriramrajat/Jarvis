import React, { useState } from 'react';
import './CommandBar.css';

export default function CommandBar({ onSend, jarvisState, connected }) {
  const [text, setText] = useState('');

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && text.trim() && connected) {
      onSend(text.trim());
      setText('');
    }
  };

  const isListening = jarvisState === 'LISTENING';

  return (
    <div className={`cmdbar ${isListening ? 'cmdbar--listening' : ''}`}>
      <div className="cmdbar__icon text-cyan">
        {isListening ? 'MIC' : 'CMD'}
      </div>
      <input
        type="text"
        className="cmdbar__input"
        placeholder={connected ? "Awaiting input..." : "Offline..."}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={!connected}
        autoFocus
      />
    </div>
  );
}
