import React from 'react';
import './SystemPanel.css';

export default function SystemPanel({ context }) {
  // context format from backend:
  // { cpu_percent, memory_percent, disk_percent, active_window }
  const metrics = context || {
    cpu_percent: 0,
    memory_percent: 0,
    disk_percent: 0,
    active_window: "Unknown"
  };

  const getMeterColor = (val) => {
    if (val < 50) return 'var(--cyan)';
    if (val < 85) return 'var(--orange)';
    return 'var(--red)';
  };

  const MetricBar = ({ label, value }) => (
    <div className="sys-panel__metric">
      <div className="sys-panel__metric-label text-xs text-dim">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="sys-panel__metric-bar-bg">
        <div 
          className="sys-panel__metric-bar-fill" 
          style={{ 
            transform: `scaleX(${value / 100})`,
            background: getMeterColor(value),
            /* Removing expensive box-shadow for performance */
          }} 
        />
      </div>
    </div>
  );

  return (
    <div className="sys-panel">
      <div className="sys-panel__header">
        <h2 className="font-hud text-cyan" style={{ fontSize: '18px', letterSpacing: '2px' }}>SYSTEM TELEMETRY</h2>
        <div className="sys-panel__divider" />
      </div>

      <div className="sys-panel__content">
        <MetricBar label="CPU LOAD" value={metrics.cpu_percent || 0} />
        <MetricBar label="MEMORY ALLOCATION" value={metrics.memory_percent || 0} />
        <MetricBar label="STORAGE POOL" value={metrics.disk_percent || 0} />

        <div className="sys-panel__section">
          <div className="text-xs text-dim mb-1">ACTIVE PROCESS</div>
          <div className="sys-panel__value font-hud" style={{ color: '#fff', fontSize: '13px' }}>
            {metrics.active_window || "NO SIGNAL"}
          </div>
        </div>
      </div>
    </div>
  );
}
