# JARVIS OS

> *"Sometimes you gotta run before you can walk."* — Tony Stark

A personal ambient AI operating system for your desktop. Voice-activated, context-aware, and built to feel like the real thing.

---

## What Is This?

JARVIS OS is not a chatbot. It's an intelligent AI layer that:

- Understands your intent via natural language
- Controls your desktop — opens apps, runs commands, searches the web
- Listens for a wake word and responds with a synthesized voice
- Monitors your system context in real-time
- Maintains conversation memory across sessions
- Provides an immersive Iron Man–style HUD interface

---

## Tech Stack

### Backend (Python)
| Layer | Technology |
|-------|-----------|
| API Server | FastAPI + Uvicorn |
| AI Brain | Google Gemini 2.0 Flash (OpenAI-compatible) |
| Wake Word | OpenWakeWord (local, free, no API key) |
| Speech-to-Text | Faster Whisper (local, offline) |
| Text-to-Speech | pyttsx3 (local, offline) |
| Database | SQLite + SQLAlchemy (async) |
| Event System | Custom async pub/sub Event Bus |

### Frontend (JavaScript)
| Layer | Technology |
|-------|-----------|
| UI Framework | React 19 + Vite |
| Desktop Shell | Electron 42 |
| Styling | Vanilla CSS + CSS Variables |
| Fonts | Orbitron, Exo 2 (Google Fonts) |
| Real-time | WebSocket (auto-reconnecting) |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Electron HUD                    │
│   StateOrb │ CommandBar │ Chat │ SystemPanel    │
└─────────────────────┬───────────────────────────┘
                      │ WebSocket
┌─────────────────────▼───────────────────────────┐
│                FastAPI Backend                  │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Brain   │  │  Voice   │  │  Automation  │  │
│  │ (Gemini) │  │ OWW+STT  │  │  (Desktop)   │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       └─────────────▼────────────────┘          │
│                  Event Bus                      │
│              (Async Pub/Sub)                    │
│                                                 │
│  ┌───────────┐  ┌───────────────────────────┐   │
│  │  Context  │  │       State Manager       │   │
│  │  Engine   │  │  IDLE→THINKING→SPEAKING   │   │
│  └───────────┘  └───────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- A microphone (for wake word & voice input)

### 1. Clone & Setup

```bash
git clone https://github.com/shriramrajat/Jarvis.git
cd Jarvis
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env — add your Gemini API key:
# Get it free at: https://aistudio.google.com/apikey
```

### 4. Run the Backend

```bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

### 5. Run the Frontend

```bash
cd frontend
npm install
npm run dev        # Browser only
npm run electron   # Full desktop app
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AI_API_KEY` | ✅ Yes | Gemini API key from [aistudio.google.com](https://aistudio.google.com) |
| `AI_BASE_URL` | ✅ Yes | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `AI_MODEL` | ✅ Yes | `gemini-2.0-flash` |
| `WAKE_WORD` | No | Default: `hey_jarvis` |
| `STT_MODEL` | No | Whisper model size: `tiny/base/small` |

---

## Phases

- [x] **Phase 1** — Core infrastructure (Event Bus, State Machine, WebSocket, HUD)
- [x] **Phase 2** — Intelligence & Voice (Gemini Brain, Automation Engine, Wake Word, STT, TTS)
- [ ] **Phase 3** — Memory & Context (Long-term memory, pattern recognition, habit learning)
- [ ] **Phase 4** — Proactive Mode (Scheduled tasks, anomaly detection, autonomous suggestions)
- [ ] **Phase 5** — Fully offline (Local LLM via Ollama, complete privacy mode)

---

## License

MIT — build your own JARVIS.
