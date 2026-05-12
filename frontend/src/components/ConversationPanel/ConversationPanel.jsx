/**
 * JARVIS OS — Conversation Panel
 * Shows the conversation history between user and JARVIS.
 * Auto-scrolls to latest message.
 */
import React, { useEffect, useRef } from 'react';
import './ConversationPanel.css';

function Message({ msg }) {
  const isUser = msg.role === 'user';
  const time = new Date(msg.timestamp).toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
  });

  return (
    <div className={`msg msg--${msg.role}`} style={{ animation: 'slide-in-bottom 0.2s ease' }}>
      <div className="msg__meta">
        <span className="msg__sender font-hud text-xs uppercase">
          {isUser ? 'YOU' : 'JARVIS'}
        </span>
        <span className="msg__time text-xs text-dim">{time}</span>
      </div>
      <div className={`msg__bubble ${isUser ? 'msg__bubble--user' : 'msg__bubble--jarvis'}`}>
        {msg.content}
      </div>
    </div>
  );
}

export default function ConversationPanel({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="conv-panel panel" id="conversation-panel">
      <div className="conv-panel__header">
        <span className="font-hud text-xs uppercase" style={{ letterSpacing: '0.15em', color: 'var(--cyan)' }}>
          Conversation Log
        </span>
        <span className="text-xs text-dim">{messages.length} messages</span>
      </div>

      <div className="conv-panel__messages" id="messages-container">
        {messages.length === 0 ? (
          <div className="conv-panel__empty">
            <div className="conv-panel__empty-icon">◈</div>
            <div className="text-dim" style={{ fontSize: '12px' }}>
              No conversation yet. Send a command to begin.
            </div>
          </div>
        ) : (
          messages.map((msg) => <Message key={msg.id} msg={msg} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
