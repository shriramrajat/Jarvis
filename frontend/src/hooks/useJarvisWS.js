/**
 * JARVIS OS — WebSocket hook
 * Manages the persistent WS connection to the FastAPI backend.
 * Auto-reconnects on disconnect. Provides real-time state updates.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = (window.jarvis?.wsUrl) || 'ws://127.0.0.1:8000/ws';
const RECONNECT_DELAY = 3000;

export function useJarvisWS() {
  const [connected, setConnected]   = useState(false);
  const [jarvisState, setJarvisState] = useState('IDLE');
  const [jarvisMode, setJarvisMode]   = useState('NORMAL');
  const [messages, setMessages]      = useState([]);
  const [context, setContext]        = useState(null);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('[WS] Connected to JARVIS backend');
        if (reconnectRef.current) {
          clearTimeout(reconnectRef.current);
          reconnectRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (e) {
          console.warn('[WS] Failed to parse message:', e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        console.log('[WS] Disconnected — reconnecting in 3s...');
        reconnectRef.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = (err) => {
        console.error('[WS] Error:', err);
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      reconnectRef.current = setTimeout(connect, RECONNECT_DELAY);
    }
  }, []);

  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case 'HANDSHAKE':
        setJarvisState(data.state?.state || 'IDLE');
        setJarvisMode(data.state?.mode || 'NORMAL');
        break;
      case 'STATE_CHANGED':
        setJarvisState(data.state || 'IDLE');
        setJarvisMode(data.mode || 'NORMAL');
        break;
      case 'RESPONSE':
        setMessages(prev => [...prev.slice(-99), {
          id: Date.now(),
          role: 'jarvis',
          content: data.content || data.text || JSON.stringify(data),
          timestamp: new Date().toISOString(),
        }]);
        break;
      case 'CONTEXT_UPDATE':
        setContext(data);
        break;
      case 'NOTIFICATION':
        console.log('[WS] Notification:', data);
        break;
      default:
        break;
    }
  }, []);

  const send = useCallback((type, payload = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...payload }));
    }
  }, []);

  const sendCommand = useCallback((text) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }]);
    send('TEXT_INPUT', { text });
  }, [send]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected, jarvisState, jarvisMode, messages, context, sendCommand, send };
}
