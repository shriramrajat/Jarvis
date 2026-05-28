import React, { useEffect, useRef } from 'react';
import './ConversationPanel.css';

export default function ConversationPanel({ messages, respondToPermission }) {
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
            const isRequest = msg.isPermissionRequest;
            const resolved = msg.permissionResolved; // 'allowed' | 'denied' | undefined

            return (
              <div key={msg.id || i} className={`msg msg--${isUser ? 'user' : 'jarvis'} ${isRequest ? 'msg--permission' : ''}`}>
                <div className="msg__meta">
                  <span className="msg__role font-hud">{isUser ? 'USER' : 'JARVIS'}</span>
                  {msg.timestamp && (
                    <span className="msg__time">{new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                  )}
                </div>
                <div className="msg__content">
                  {msg.content}
                  
                  {isRequest && (
                    <div className="msg__permission-card">
                      <div className="msg__permission-details font-hud text-xs">
                        <div>ACTION: <span className="text-amber">{msg.action}</span></div>
                        {msg.params && msg.params.command && (
                          <div className="text-dim">CMD: <code>{msg.params.command}</code></div>
                        )}
                        {msg.params && msg.params.op && (
                          <div className="text-dim">OP: <code>{msg.params.op}</code> on <code>{msg.params.path}</code></div>
                        )}
                      </div>

                      {!resolved ? (
                        <div className="msg__permission-actions">
                          <button
                            className="btn btn--cyan btn--xs"
                            onClick={() => respondToPermission(msg.command_id, true)}
                          >
                            ALLOW
                          </button>
                          <button
                            className="btn btn--red btn--xs"
                            onClick={() => respondToPermission(msg.command_id, false)}
                          >
                            DENY
                          </button>
                        </div>
                      ) : (
                        <div className={`msg__permission-status font-hud text-xs ${resolved === 'allowed' ? 'text-cyan' : 'text-red'}`}>
                          ● ACTION {resolved.toUpperCase()}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}