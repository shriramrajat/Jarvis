"""
JARVIS OS — Automation Engine
Executes actions dispatched by the Brain Engine.

Phase 2 capabilities:
  - OPEN_APP: Launch any Windows application
  - RUN_COMMAND: Execute whitelisted terminal commands
  - SEARCH_WEB: Open browser with search query
  - OPEN_URL: Open a specific URL
  - SYSTEM_INFO: Return CPU/RAM/disk stats
  - SET_MODE: Change JARVIS operating mode

Each action publishes EXECUTION_COMPLETED or EXECUTION_FAILED event.
High-risk commands are validated against a whitelist before execution.
"""
import asyncio
import subprocess
import webbrowser
import urllib.parse
import psutil
import platform
from loguru import logger

from ...config import settings
from ...event_bus import event_bus, Event, EventType
from ...state import state_manager, JarvisState, JarvisMode


# ── Whitelisted commands (LOW/MEDIUM risk — auto-execute) ─────────────────────
# These are considered safe to run without confirmation.

SAFE_COMMAND_PREFIXES = [
    "echo", "dir", "ls", "pwd", "whoami", "hostname",
    "ipconfig", "ping", "curl", "python", "node", "npm",
    "git status", "git log", "git diff", "git branch",
    "type ", "cat ", "more ", "where ", "which ",
]


# ── App name → executable mapping ─────────────────────────────────────────────

APP_MAP = {
    # Editors / IDEs
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "notepad++": "notepad++",
    "sublime": "subl",
    # Browsers
    "chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "brave": "brave",
    # Terminal
    "terminal": "wt",
    "powershell": "powershell",
    "cmd": "cmd",
    "windows terminal": "wt",
    # Dev tools
    "postman": "postman",
    "docker": "docker desktop",
    "github desktop": "github desktop",
    # Productivity
    "task manager": "taskmgr",
    "file explorer": "explorer",
    "explorer": "explorer",
    "calculator": "calc",
    "paint": "mspaint",
    # Communication
    "discord": "discord",
    "slack": "slack",
    "teams": "teams",
    "zoom": "zoom",
    "spotify": "spotify",
    # Office
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
}


class AutomationEngine:
    """
    Listens for EXECUTION_STARTED events and dispatches to the correct handler.
    Returns results via EXECUTION_COMPLETED / EXECUTION_FAILED events.
    """

    def __init__(self):
        self._action_map = {
            "OPEN_APP":       self._open_app,
            "RUN_COMMAND":    self._run_command,
            "SEARCH_WEB":     self._search_web,
            "OPEN_URL":       self._open_url,
            "SYSTEM_INFO":    self._system_info,
            "SET_MODE":       self._set_mode,
            "FILE_OPERATION": self._file_operation,
            "WORKFLOW":       self._workflow,
            "REMEMBER":       self._noop,   # Handled by memory engine
            "RECALL":         self._noop,   # Handled by memory engine
        }

    # ── Event Handler ───────────────────────────────────────────────────────────

    async def _handle_execution(self, event: Event) -> None:
        action     = event.data.get("action", "")
        params     = event.data.get("params", {})
        command_id = event.data.get("command_id", "")

        logger.info(f"[Automation] Executing: {action} | params={params}")

        # Transition to EXECUTING state
        await state_manager.transition(JarvisState.EXECUTING, source="automation")

        handler = self._action_map.get(action)
        if not handler:
            logger.warning(f"[Automation] No handler for action: {action}")
            await state_manager.transition(JarvisState.IDLE, source="automation")
            return

        try:
            result = await handler(params)
            await event_bus.publish(Event(
                type=EventType.EXECUTION_COMPLETED,
                data={"command_id": command_id, "action": action, "result": result},
                source="automation",
                priority="MEDIUM",
            ))
        except Exception as e:
            logger.error(f"[Automation] {action} failed: {e}")
            await event_bus.publish(Event(
                type=EventType.EXECUTION_FAILED,
                data={"command_id": command_id, "action": action, "error": str(e)},
                source="automation",
                priority="HIGH",
            ))
        finally:
            # Return to IDLE (SPEAKING handles its own transition via TTS engine)
            if state_manager.state == JarvisState.EXECUTING:
                await state_manager.transition(JarvisState.IDLE, source="automation")

    # ── Action Handlers ─────────────────────────────────────────────────────────

    async def _open_app(self, params: dict) -> dict:
        app_name = params.get("app", "").lower().strip()

        # Resolve from map
        executable = APP_MAP.get(app_name, app_name)

        logger.info(f"[Automation] Opening app: '{executable}'")
        subprocess.Popen(
            executable,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return {"launched": executable}

    async def _run_command(self, params: dict) -> dict:
        command = params.get("command", "").strip()
        if not command:
            raise ValueError("No command specified")

        # Safety check — validate against whitelist for auto-execution
        is_safe = any(command.lower().startswith(pfx) for pfx in SAFE_COMMAND_PREFIXES)
        if not is_safe and settings.REQUIRE_CONFIRMATION_HIGH_RISK:
            raise PermissionError(f"Command '{command}' requires manual confirmation")

        logger.info(f"[Automation] Running command: {command}")
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode(errors="replace") or stderr.decode(errors="replace")
        return {"output": output[:2000], "returncode": proc.returncode}

    async def _search_web(self, params: dict) -> dict:
        query = params.get("query", "")
        engine = params.get("engine", "google")
        engines = {
            "google": "https://www.google.com/search?q=",
            "bing": "https://www.bing.com/search?q=",
            "duckduckgo": "https://duckduckgo.com/?q=",
        }
        base = engines.get(engine, engines["google"])
        url = base + urllib.parse.quote_plus(query)
        webbrowser.open(url)
        return {"url": url, "query": query}

    async def _open_url(self, params: dict) -> dict:
        url = params.get("url", "")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return {"url": url}

    async def _system_info(self, params: dict) -> dict:
        metric = params.get("metric", "all")
        info = {}

        if metric in ("cpu", "all"):
            info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
            info["cpu_cores"]   = psutil.cpu_count()

        if metric in ("memory", "ram", "all"):
            mem = psutil.virtual_memory()
            info["memory_total_gb"]   = round(mem.total / 1e9, 1)
            info["memory_used_gb"]    = round(mem.used  / 1e9, 1)
            info["memory_percent"]    = mem.percent

        if metric in ("disk", "all"):
            disk = psutil.disk_usage("/")
            info["disk_total_gb"] = round(disk.total / 1e9, 1)
            info["disk_free_gb"]  = round(disk.free  / 1e9, 1)
            info["disk_percent"]  = disk.percent

        if metric in ("system", "all"):
            info["os"]       = platform.system()
            info["os_ver"]   = platform.version()
            info["hostname"] = platform.node()

        return info

    async def _set_mode(self, params: dict) -> dict:
        mode_str = params.get("mode", "NORMAL").upper()
        try:
            mode = JarvisMode[mode_str]
        except KeyError:
            raise ValueError(f"Unknown mode: {mode_str}")
        await state_manager.set_mode(mode, source="automation")
        return {"mode": mode_str}

    async def _file_operation(self, params: dict) -> dict:
        # Phase 3 — basic stub for now
        logger.warning("[Automation] File operations are Phase 3")
        return {"status": "not_implemented", "phase": 3}

    async def _workflow(self, params: dict) -> dict:
        """Executes a multi-step routine sequentially."""
        steps = params.get("steps", [])
        if not steps:
            return {"status": "empty_workflow"}

        logger.info(f"[Automation] Starting workflow with {len(steps)} steps")
        results = []
        
        for idx, step in enumerate(steps):
            step_action = step.get("action")
            step_params = step.get("params", {})
            
            logger.info(f"[Automation] Workflow Step {idx+1}/{len(steps)}: {step_action}")
            
            handler = self._action_map.get(step_action)
            if not handler:
                logger.warning(f"[Automation] Workflow step failed — unknown action: {step_action}")
                results.append({"step": idx+1, "action": step_action, "status": "failed", "error": "Unknown action"})
                continue
                
            try:
                # Add slight delay between steps so we don't overwhelm the system
                if idx > 0:
                    await asyncio.sleep(1.0)
                
                step_result = await handler(step_params)
                results.append({"step": idx+1, "action": step_action, "status": "success", "result": step_result})
            except Exception as e:
                logger.error(f"[Automation] Workflow step failed: {e}")
                results.append({"step": idx+1, "action": step_action, "status": "failed", "error": str(e)})

        return {"status": "completed", "steps_executed": len(steps), "results": results}

    async def _noop(self, params: dict) -> dict:
        return {"status": "delegated"}

    # ── Lifecycle ───────────────────────────────────────────────────────────────

    async def start(self) -> None:
        event_bus.subscribe(EventType.EXECUTION_STARTED, self._handle_execution)
        logger.success("[Automation] Started")

    async def stop(self) -> None:
        event_bus.unsubscribe(EventType.EXECUTION_STARTED, self._handle_execution)
        logger.info("[Automation] Stopped")


# ── Singleton ──────────────────────────────────────────────────────────────────

automation_engine = AutomationEngine()
