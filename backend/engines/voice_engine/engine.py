"""
JARVIS OS — Voice Engine
Handles the complete voice interaction pipeline:
  1. Wake Word — OpenWakeWord (no API key, runs locally)
  2. Speech-to-Text — Faster Whisper (local, offline)
  3. Text-to-Speech — pyttsx3 (local, offline, fallback)
     Phase 3 upgrade: Piper TTS for higher quality voice

Pipeline flow:
  Mic → OpenWakeWord → [wake detected] → Faster Whisper → TEXT → Brain Engine
  Brain response → TTS → Audio output

The voice engine runs in a background thread (audio I/O is blocking).
It publishes events to the Event Bus for thread-safe integration.
"""
import asyncio
import threading
import io
import queue
import time
import numpy as np
from loguru import logger

from ...config import settings
from ...event_bus import event_bus, Event, EventType
from ...state import state_manager, JarvisState


class VoiceEngine:
    """
    Voice pipeline manager. Runs audio processing in daemon threads
    and bridges results back to the async Event Bus.
    """

    def __init__(self):
        self._running        = False
        self._listening      = False
        self._loop: asyncio.AbstractEventLoop | None = None

        # Lazy-loaded heavy models
        self._oww_model      = None    # OpenWakeWord
        self._whisper_model  = None    # Faster Whisper
        self._tts_engine     = None    # pyttsx3

        # Thread-safe queues
        self._tts_queue: queue.Queue = queue.Queue()

        self._wake_thread:   threading.Thread | None = None
        self._tts_thread:    threading.Thread | None = None

    # ── Model Loading (lazy) ────────────────────────────────────────────────────

    def _load_wake_word_model(self):
        """Load OpenWakeWord model. Downloads ~10MB on first run."""
        try:
            import openwakeword
            from openwakeword.model import Model

            # Auto-download the hey_jarvis model if not present
            openwakeword.utils.download_models([settings.WAKE_WORD])

            self._oww_model = Model(
                wakeword_models=[settings.WAKE_WORD],
                inference_framework="onnx",
            )
            logger.success(f"[Voice] OpenWakeWord loaded — listening for '{settings.WAKE_WORD}'")
        except Exception as e:
            logger.error(f"[Voice] OpenWakeWord load failed: {e}")
            raise

    def _load_whisper_model(self):
        """Load Faster Whisper model. Downloads on first run (~150MB for 'base')."""
        try:
            from faster_whisper import WhisperModel
            self._whisper_model = WhisperModel(
                settings.STT_MODEL,
                device="cpu",
                compute_type="int8",
            )
            logger.success(f"[Voice] Faster Whisper loaded — model={settings.STT_MODEL}")
        except Exception as e:
            logger.error(f"[Voice] Faster Whisper load failed: {e}")
            raise

    def _load_tts_engine(self):
        """Load pyttsx3 TTS (zero-download, works immediately)."""
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 165)    # Slightly slower = more JARVIS-like
            self._tts_engine.setProperty("volume", 0.9)

            # Try to use a male voice
            voices = self._tts_engine.getProperty("voices")
            for voice in voices:
                if "david" in voice.name.lower() or "mark" in voice.name.lower():
                    self._tts_engine.setProperty("voice", voice.id)
                    break

            logger.success("[Voice] pyttsx3 TTS engine loaded")
        except Exception as e:
            logger.warning(f"[Voice] TTS load failed (will skip TTS): {e}")

    # ── Wake Word Detection ─────────────────────────────────────────────────────

    def _wake_word_loop(self):
        """
        Runs in a daemon thread. Continuously listens for wake word.
        When detected, captures 5 seconds of audio and transcribes it.
        """
        try:
            import sounddevice as sd
            SAMPLE_RATE  = 16000
            CHUNK        = 1280   # 80ms at 16kHz — required by OpenWakeWord

            logger.info("[Voice] Wake word listener started")
            audio_buffer = []

            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK,
            ) as stream:
                while self._running:
                    if self._listening:
                        time.sleep(0.05)
                        continue

                    chunk, _ = stream.read(CHUNK)
                    audio_16k = (chunk[:, 0] * 32767).astype(np.int16)

                    prediction = self._oww_model.predict(audio_16k)
                    score = list(prediction.values())[0]

                    if score > 0.5:
                        logger.info(f"[Voice] Wake word detected! score={score:.2f}")
                        self._publish_async(Event(
                            type=EventType.WAKE_WORD_DETECTED,
                            data={"score": float(score), "wake_word": settings.WAKE_WORD},
                            source="voice",
                            priority="HIGH",
                        ))

                        # Capture command audio (4 seconds)
                        self._listening = True
                        self._publish_async(Event(
                            type=EventType.LISTENING_STARTED,
                            data={},
                            source="voice",
                            priority="HIGH",
                        ))

                        # Collect 4s of audio
                        capture_frames = []
                        for _ in range(int(SAMPLE_RATE * 4 / CHUNK)):
                            frame, _ = stream.read(CHUNK)
                            capture_frames.append(frame[:, 0])

                        self._listening = False
                        self._publish_async(Event(
                            type=EventType.LISTENING_STOPPED,
                            data={},
                            source="voice",
                            priority="MEDIUM",
                        ))

                        audio_np = np.concatenate(capture_frames)
                        self._transcribe_async(audio_np, SAMPLE_RATE)

        except Exception as e:
            logger.error(f"[Voice] Wake word loop crashed: {e}")

    def _transcribe_async(self, audio_np: np.ndarray, sample_rate: int):
        """Run Whisper transcription in a thread and publish result."""
        def _do_transcribe():
            try:
                segments, info = self._whisper_model.transcribe(
                    audio_np.astype(np.float32),
                    language="en",
                    beam_size=3,
                    vad_filter=True,
                )
                text = " ".join(s.text for s in segments).strip()
                if text:
                    logger.info(f"[Voice] Transcribed: '{text}'")
                    asyncio.run_coroutine_threadsafe(
                        event_bus.publish(Event(
                            type=EventType.VOICE_INPUT,
                            data={"text": text, "source": "voice"},
                            source="voice",
                            priority="HIGH",
                        )),
                        self._loop,
                    )
                else:
                    logger.debug("[Voice] Empty transcription — ignoring")
                    asyncio.run_coroutine_threadsafe(
                        state_manager.transition(JarvisState.IDLE, source="voice"),
                        self._loop,
                    )
            except Exception as e:
                logger.error(f"[Voice] Transcription failed: {e}")

        threading.Thread(target=_do_transcribe, daemon=True).start()

    # ── TTS ─────────────────────────────────────────────────────────────────────

    def _tts_loop(self):
        """Background thread that drains the TTS queue."""
        while self._running:
            try:
                text = self._tts_queue.get(timeout=1.0)
                if self._tts_engine:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                self._tts_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[Voice] TTS error: {e}")

    def _speak(self, text: str):
        """Queue text for TTS playback."""
        if text:
            self._tts_queue.put(text)

    async def _handle_tts_speak(self, event: Event) -> None:
        """Handle TTS_SPEAK events from the brain."""
        text = event.data.get("text", "")
        self._speak(text)

    async def _handle_response_generated(self, event: Event) -> None:
        """Auto-speak every JARVIS response."""
        text = event.data.get("text", "")
        if text:
            # Use force_state — response may arrive after state already returned to IDLE
            await state_manager.force_state(JarvisState.SPEAKING)
            await event_bus.publish(Event(
                type=EventType.STATE_CHANGED,
                data=state_manager.snapshot.to_dict(),
                source="voice",
                priority="MEDIUM",
            ))
            self._speak(text)
            await asyncio.sleep(0.5)
            await state_manager.force_state(JarvisState.IDLE)
            await event_bus.publish(Event(
                type=EventType.STATE_CHANGED,
                data=state_manager.snapshot.to_dict(),
                source="voice",
                priority="MEDIUM",
            ))

    # ── Async/Thread Bridge ─────────────────────────────────────────────────────

    def _publish_async(self, event: Event):
        """Thread-safe event publishing into the async event loop."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                event_bus.publish(event),
                self._loop,
            )

    async def _background_init(self) -> None:
        """Load all voice models in background — server stays responsive."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._load_tts_engine)
            await loop.run_in_executor(None, self._load_wake_word_model)
            await loop.run_in_executor(None, self._load_whisper_model)

            # Subscribe to response events for TTS
            event_bus.subscribe(EventType.TTS_SPEAK,          self._handle_tts_speak)
            event_bus.subscribe(EventType.RESPONSE_GENERATED, self._handle_response_generated)

            # Start background threads
            self._wake_thread = threading.Thread(
                target=self._wake_word_loop, daemon=True, name="jarvis-wake"
            )
            self._wake_thread.start()

            self._tts_thread = threading.Thread(
                target=self._tts_loop, daemon=True, name="jarvis-tts"
            )
            self._tts_thread.start()

            logger.success("[Voice] Engine fully online — say 'hey jarvis' to activate")

        except Exception as e:
            logger.error(f"[Voice] Model loading failed: {e}")
            logger.warning("[Voice] Running in text-only mode (TTS via pyttsx3 if available)")
            # Still hook into response events for TTS if engine loaded
            if self._tts_engine:
                event_bus.subscribe(EventType.RESPONSE_GENERATED, self._handle_response_generated)
                self._tts_thread = threading.Thread(
                    target=self._tts_loop, daemon=True, name="jarvis-tts"
                )
                self._tts_thread.start()

    # ── Lifecycle ───────────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True
        self._loop = asyncio.get_event_loop()
        logger.info("[Voice] Starting in background (models load asynchronously)...")
        # Fire and forget — models download/load without blocking server startup
        asyncio.create_task(self._background_init())

    async def stop(self) -> None:
        self._running = False
        logger.info("[Voice] Stopped")


# ── Singleton ──────────────────────────────────────────────────────────────────

voice_engine = VoiceEngine()
