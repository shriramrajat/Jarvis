/**
 * JARVIS OS — System Panel
 * Right sidebar showing live system metrics: CPU, RAM, active app, context.
 */
import React from 'react';
import './SystemPanel.css';

function MetricBar({ label, value, color = 'var(--cyan)', id }) {
  const pct = Math.min(100, Math.round(value || 0));
  const getColor = (v) => {
    if (v > 85) return 'var(--red)';
    if (v > 60) return 'var(--amber)';
    return color;
  };
  const barColor = getColor(pct);

  return (
    <div className="metric" id={id}>
      <div className="metric__header">
        <span className="metric__label text-xs uppercase text-dim">{label}</span>
        <span className="metric__value font-hud text-xs" style={{ color: barColor }}>{pct}%</span>
      </div>
      <div className="metric__track">
        <div
          className="metric__fill"
          style={{ width: `${pct}%`, background: barColor, boxShadow: `0 0 6px ${barColor}` }}
        />
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="info-row">
      <span className="info-row__label text-xs uppercase text-dim">{label}</span>
      <span className="info-row__value text-xs" style={{ color: 'var(--text-primary)' }}>
        {value || '—'}
      </span>
    </div>
  );
}

export default function SystemPanel({ context }) {
  return (
    <div className="sys-panel panel" id="system-panel">
      <div className="sys-panel__header">
        <span className="font-hud text-xs uppercase text-cyan" style={{ letterSpacing: '0.15em' }}>
          System Status
        </span>
        <div className="sys-panel__indicator" />
      </div>

      <div className="sys-panel__section">
        <MetricBar id="metric-cpu" label="CPU" value={context?.cpu_percent} color="var(--cyan)" />
        <MetricBar id="metric-ram" label="RAM" value={context?.memory_percent} color="var(--purple)" />
      </div>

      <div className="sys-panel__divider" />

      <div className="sys-panel__section">
        <InfoRow label="Active App" value={context?.active_app} />
        <InfoRow
          label="Window"
          value={context?.active_window_title
            ? context.active_window_title.length > 28
              ? context.active_window_title.slice(0, 28) + '…'
              : context.active_window_title
            : '—'
          }
        />
        <InfoRow label="Project" value={context?.current_project} />
        <InfoRow label="Task" value={context?.current_task} />
      </div>

      <div className="sys-panel__divider" />

      <div className="sys-panel__section">
        <span className="text-xs uppercase text-dim" style={{ letterSpacing: '0.1em' }}>
          Recent Intents
        </span>
        <div className="sys-panel__intents">
          {(context?.recent_intents || []).slice(-4).reverse().map((intent, i) => (
            <div key={i} className="sys-panel__intent text-xs text-dim">
              {intent}
            </div>
          ))}
          {(!context?.recent_intents || context.recent_intents.length === 0) && (
            <div className="text-xs text-dim" style={{ fontStyle: 'italic' }}>No recent intents</div>
          )}
        </div>
      </div>
    </div>
  );
}
