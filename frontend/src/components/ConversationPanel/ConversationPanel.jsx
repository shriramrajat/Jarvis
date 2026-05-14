import React, { useEffect, useRef } from 'react';
import './ConversationPanel.css';

export default function ConversationPanel({ messages }) {
  const scrollRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="conv-panel">
      <div className="conv-panel__header">
        <h2 className="font-hud text-cyan" style={{ fontSize: '18px', letterSpacing: '2px' }}>CONVERSATION LOG</h2>
        <div className="conv-panel__divider" />
      </div>

      <div className="conv-panel__scroll" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="conv-panel__empty text-dim text-sm">No recent interactions.</div>
        ) : (
          messages.map((msg, i) => {
            const isUser = msg.role === 'user';
            return (
              <div key={msg.id || i} className={`msg msg--${isUser ? 'user' : 'jarvis'}`}>
                <div className="msg__meta">
                  <span className="msg__role font-hud">{isUser ? 'USER' : 'JARVIS'}</span>
                  {msg.timestamp && (
                    <span className="msg__time">{new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                  )}
                </div>
                <div className="msg__content">
                  {msg.content}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}