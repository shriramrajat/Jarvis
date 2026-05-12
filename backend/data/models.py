"""
JARVIS OS — SQLAlchemy Database Models
SQLite via aiosqlite for async operations.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Conversations ──────────────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id           = Column(String(36), primary_key=True)
    session_id   = Column(String(36), nullable=False, index=True)
    role         = Column(String(16), nullable=False)   # "user" | "jarvis"
    content      = Column(Text, nullable=False)
    intent       = Column(String(128), nullable=True)
    context_snap = Column(JSON, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_conv_session_created", "session_id", "created_at"),
    )


# ── Memory / Knowledge ────────────────────────────────────────────────────────

class Memory(Base):
    __tablename__ = "memories"

    id           = Column(String(36), primary_key=True)
    memory_type  = Column(String(32), nullable=False, index=True)  # fact | preference | workflow | pattern
    content      = Column(Text, nullable=False)
    summary      = Column(Text, nullable=True)
    tags         = Column(JSON, default=list)
    importance   = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at   = Column(DateTime, nullable=True)


# ── User Preferences ──────────────────────────────────────────────────────────

class Preference(Base):
    __tablename__ = "preferences"

    id         = Column(String(36), primary_key=True)
    key        = Column(String(128), unique=True, nullable=False)
    value      = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Automation Logs ───────────────────────────────────────────────────────────

class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id          = Column(String(36), primary_key=True)
    action_type = Column(String(64), nullable=False, index=True)  # open_app | run_command | browser | file
    command     = Column(Text, nullable=False)
    params      = Column(JSON, default=dict)
    status      = Column(String(16), nullable=False)   # success | failed | denied
    risk_level  = Column(String(8), default="LOW")     # LOW | MEDIUM | HIGH
    duration_ms = Column(Integer, nullable=True)
    error       = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_auto_type_status", "action_type", "status"),
    )


# ── Observation Snapshots ─────────────────────────────────────────────────────

class ObservationSnapshot(Base):
    __tablename__ = "observation_snapshots"

    id            = Column(String(36), primary_key=True)
    active_app    = Column(String(128), nullable=True)
    window_title  = Column(Text, nullable=True)
    cpu_percent   = Column(Float, nullable=True)
    memory_percent= Column(Float, nullable=True)
    raw_data      = Column(JSON, default=dict)
    created_at    = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_obs_app_created", "active_app", "created_at"),
    )


# ── System Events Log ─────────────────────────────────────────────────────────

class SystemEventLog(Base):
    __tablename__ = "system_event_logs"

    id         = Column(String(36), primary_key=True)
    event_type = Column(String(64), nullable=False, index=True)
    source     = Column(String(64), nullable=True)
    data       = Column(JSON, default=dict)
    priority   = Column(String(8), default="MEDIUM")
    created_at = Column(DateTime, default=datetime.utcnow)
