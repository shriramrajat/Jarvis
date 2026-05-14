"""
JARVIS OS — AI Brain Engine
The central intelligence. Connects to any OpenAI-compatible API (Groq, Gemini, DeepSeek).

Responsibilities:
  - Subscribe to TEXT_INPUT + VOICE_INPUT events
  - Build contextual prompts with memory + current context
  - Call AI API for intent classification + response generation
  - Parse intent + plan tasks
  - Publish RESPONSE_GENERATED and EXECUTION_STARTED events
  - Integrate with Memory Engine for persistent context

Phase 2: Basic conversation + intent classification + simple task dispatch.
Phase 3: Memory-augmented reasoning, REMEMBER/RECALL, preference learning.
"""
import asyncio
import json
from openai import AsyncOpenAI
from loguru import logger

from ...config import settings
from ...event_bus import event_bus, Event, EventType
from ...state import state_manager, JarvisState
from ..memory_engine import memory_engine
from ..personality_engine import personality_engine


# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """CRITICAL: You MUST respond with ONLY a valid JSON object. No markdown, no explanation, no text before or after the JSON. Raw JSON only.

You are JARVIS, an intelligent ambient AI desktop assistant.
You are running on the user's Windows PC and have the ability to control it.

Your personality:
- Direct, intelligent, efficient — like Tony Stark's JARVIS
- Concise responses — no unnecessary filler
- Confirm what you're doing before doing it for HIGH-RISK actions
- Always address the user as "sir" (or by name if known)

Your capabilities (available tools):
- OPEN_APP: Open any application by name
- RUN_COMMAND: Execute a terminal/shell command
- SEARCH_WEB: Open a web search in the browser
- OPEN_URL: Open a specific URL
- FILE_OPERATION: Create, move, read files/folders
- SYSTEM_INFO: Get system stats (CPU, RAM, disk)
- SET_MODE: Change JARVIS operating mode (FOCUS, OBSERVATION, NORMAL)
- REMEMBER: Store something in memory
- RECALL: Retrieve from memory
- WORKFLOW: Execute a sequence of multiple actions sequentially
- NONE: Conversational response only — no action needed

Risk levels:
- LOW: Open apps, search, info queries → execute immediately
- MEDIUM: File reads, URL opens → execute immediately
- HIGH: Delete files, run arbitrary commands, form submissions → ask confirmation first

Respond in this exact JSON format:
{
  "response": "What you say to the user",
  "action": "OPEN_APP | RUN_COMMAND | SEARCH_WEB | OPEN_URL | FILE_OPERATION | SYSTEM_INFO | SET_MODE | REMEMBER | RECALL | WORKFLOW | NONE",
  "params": {},
  "risk": "LOW | MEDIUM | HIGH",
  "requires_confirmation": false
}

Examples:
User: "open vs code"
→ {"response": "Opening Visual Studio Code.", "action": "OPEN_APP", "params": {"app": "code"}, "risk": "LOW", "requires_confirmation": false}

User: "run my morning routine"
→ {"response": "Good morning, sir. Starting your workflow.", "action": "WORKFLOW", "params": {"steps": [{"action": "OPEN_URL", "params": {"url": "mail.google.com"}}, {"action": "OPEN_APP", "params": {"app": "spotify"}}]}, "risk": "LOW", "requires_confirmation": false}

User: "what's my cpu usage"
→ {"response": "Fetching system metrics.", "action": "SYSTEM_INFO", "params": {"metric": "cpu"}, "risk": "LOW", "requires_confirmation": false}

User: "delete all files in downloads"
→ {"response": "That will permanently delete all files in your Downloads folder. Shall I proceed?", "action": "FILE_OPERATION", "params": {"op": "delete", "path": "~/Downloads/*"}, "risk": "HIGH", "requires_confirmation": true}

User: "hello" / "how are you"
→ {"response": "All systems operational, sir. How can I assist?", "action": "NONE", "params": {}, "risk": "LOW", "requires_confirmation": false}
"""


# ── Brain Engine ───────────────────────────────────────────────────────────────

class BrainEngine:
    """
    The AI reasoning core. Subscribes to input events, calls DeepSeek,
    publishes responses and execution intents.
    """

    def __init__(self):
        self._client: AsyncOpenAI | None = None
        self._conversation_history: list[dict] = []
        self._max_history = 20          # Keep last 20 exchanges in context
        self._ready = False

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            if not settings.AI_API_KEY:
                raise ValueError("AI_API_KEY is not set in .env")
            self._client = AsyncOpenAI(
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
            )
        return self._client

    async def _build_messages(self, user_input: str, context: dict | None = None) -> list[dict]:
        """Build the message list for the API call with memory + context injection."""
        
        # ── Phase 3: Dynamic Personality Modifiers ──
        base_prompt = SYSTEM_PROMPT
        modifiers = personality_engine.get_dynamic_prompt_modifiers()
        if modifiers:
            base_prompt += "\n" + modifiers

        messages = [{"role": "system", "content": base_prompt}]

        # Inject current context as a system note
        if context:
            ctx_note = (
                f"\n[CURRENT CONTEXT]\n"
                f"Active app: {context.get('active_app', 'unknown')}\n"
                f"Window: {context.get('active_window_title', '')}\n"
                f"CPU: {context.get('cpu_percent', 0):.1f}%  RAM: {context.get('memory_percent', 0):.1f}%\n"
                f"Mode: {state_manager.mode.value}\n"
            )
            messages.append({"role": "system", "content": ctx_note})

        # ── Phase 3: Inject memory context ──────────────────────────────────
        try:
            mem_ctx = await memory_engine.build_memory_context(user_input)

            # Inject relevant memories
            if mem_ctx.get("relevant_memories"):
                mem_text = "\n[RELEVANT MEMORIES]\n"
                for mem in mem_ctx["relevant_memories"]:
                    mem_text += f"- [{mem['type']}] {mem['content']}\n"
                messages.append({"role": "system", "content": mem_text})

            # Inject user preferences
            if mem_ctx.get("preferences"):
                pref_text = "\n[USER PREFERENCES]\n"
                for k, v in mem_ctx["preferences"].items():
                    pref_text += f"- {k}: {v}\n"
                messages.append({"role": "system", "content": pref_text})

            # Add conversation history from persistent storage
            if mem_ctx.get("recent_conversations"):
                for turn in mem_ctx["recent_conversations"]:
                    # Map 'jarvis' → 'assistant' for API compatibility
                    role = "assistant" if turn["role"] == "jarvis" else turn["role"]
                    messages.append({"role": role, "content": turn["content"]})
            else:
                # Fallback to in-memory history if memory engine has no data yet
                messages.extend(self._conversation_history[-self._max_history:])

        except Exception as e:
            logger.warning(f"[Brain] Memory context failed, using in-memory fallback: {e}")
            messages.extend(self._conversation_history[-self._max_history:])

        # Add current user message
        messages.append({"role": "user", "content": user_input})
        return messages

    def _parse_response(self, raw: str) -> dict:
        """Parse the JSON response from DeepSeek. Fallback to plain text if malformed."""
        raw = raw.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"[Brain] Non-JSON response, treating as plain text")
            return {
                "response": raw,
                "action": "NONE",
                "params": {},
                "risk": "LOW",
                "requires_confirmation": False,
            }

    async def _call_ai(self, user_input: str, context: dict | None = None) -> dict:
        """Make the API call and return parsed result."""
        client = self._get_client()
        messages = await self._build_messages(user_input, context)

        logger.info(f"[Brain] → {settings.AI_MODEL} @ {settings.AI_BASE_URL[:40]} | '{user_input[:50]}...'")

        response = await client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_TOKENS,
        )

        raw = response.choices[0].message.content
        logger.debug(f"[Brain] ← raw: {raw[:200]}")

        # Update in-memory history (fallback)
        self._conversation_history.append({"role": "user", "content": user_input})
        self._conversation_history.append({"role": "assistant", "content": raw})

        return self._parse_response(raw)

    # ── Event Handlers ──────────────────────────────────────────────────────────

    async def _handle_text_input(self, event: Event) -> None:
        """Handle TEXT_INPUT or VOICE_INPUT events."""
        user_input = event.data.get("text", "").strip()
        if not user_input:
            return

        command_id = event.data.get("command_id", "")
        context    = event.data.get("context")

        logger.info(f"[Brain] Processing: '{user_input}'")

        try:
            result = await self._call_ai(user_input, context)
        except Exception as e:
            logger.error(f"[Brain] AI call failed: {e}")
            await state_manager.transition(JarvisState.ERROR, source="brain")
            await event_bus.publish(Event(
                type=EventType.RESPONSE_GENERATED,
                data={
                    "command_id": command_id,
                    "text": f"I encountered an error: {str(e)}",
                    "action": "NONE",
                    "risk": "LOW",
                    "requires_confirmation": False,
                },
                source="brain",
                priority="HIGH",
            ))
            await state_manager.transition(JarvisState.IDLE, source="brain")
            return

        response_text        = result.get("response", "")
        action               = result.get("action", "NONE")
        params               = result.get("params", {})
        risk                 = result.get("risk", "LOW")
        requires_confirmation = result.get("requires_confirmation", False)

        # Check if confirmation is needed for high-risk actions
        if requires_confirmation and settings.REQUIRE_CONFIRMATION_HIGH_RISK:
            await state_manager.transition(JarvisState.WAITING_CONFIRM, source="brain")
            await event_bus.publish(Event(
                type=EventType.PERMISSION_REQUIRED,
                data={
                    "command_id": command_id,
                    "message": response_text,
                    "action": action,
                    "params": params,
                    "risk": risk,
                },
                source="brain",
                priority="HIGH",
            ))
            return

        # Publish the spoken/displayed response
        await event_bus.publish(Event(
            type=EventType.RESPONSE_GENERATED,
            data={
                "command_id": command_id,
                "text": response_text,
                "action": action,
                "params": params,
                "risk": risk,
                "requires_confirmation": False,
            },
            source="brain",
            priority="HIGH",
        ))

        # ── Phase 3: Handle REMEMBER / RECALL actions ────────────────────
        if action == "REMEMBER":
            # Store the user's original input as the memory (or AI-extracted content if available)
            content_to_store = params.get("content", params.get("text", user_input))
            mem_type = params.get("type", "fact")
            importance = params.get("importance", 0.7)
            await memory_engine.store_memory(
                content=content_to_store,
                memory_type=mem_type,
                importance=importance,
            )
            logger.info(f"[Brain] Stored memory: {content_to_store[:60]}")

        elif action == "RECALL":
            query = params.get("query", params.get("text", ""))
            memories = await memory_engine.search_memories(query, limit=5)
            if memories:
                mem_text = "\n".join(f"- {m['content']}" for m in memories)
                logger.info(f"[Brain] Recalled {len(memories)} memories")
            else:
                logger.info("[Brain] No memories found for recall")

        # If there's an action to execute — fire it
        elif action != "NONE":
            await event_bus.publish(Event(
                type=EventType.EXECUTION_STARTED,
                data={
                    "command_id": command_id,
                    "action": action,
                    "params": params,
                    "risk": risk,
                },
                source="brain",
                priority="HIGH",
            ))

    async def _handle_voice_input(self, event: Event) -> None:
        """Voice input is the same flow as text input."""
        await self._handle_text_input(event)

    async def clear_history(self) -> None:
        """Clear conversation context (new session)."""
        self._conversation_history.clear()
        logger.info("[Brain] Conversation history cleared")

    # ── Lifecycle ───────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Register event subscriptions."""
        event_bus.subscribe(EventType.TEXT_INPUT,  self._handle_text_input)
        event_bus.subscribe(EventType.VOICE_INPUT, self._handle_voice_input)
        self._ready = True
        logger.success(f"[Brain] Started — model={settings.AI_MODEL} base={settings.AI_BASE_URL}")

    async def stop(self) -> None:
        event_bus.unsubscribe(EventType.TEXT_INPUT,  self._handle_text_input)
        event_bus.unsubscribe(EventType.VOICE_INPUT, self._handle_voice_input)
        logger.info("[Brain] Stopped")


# ── Singleton ──────────────────────────────────────────────────────────────────

brain_engine = BrainEngine()
