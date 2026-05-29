import pytest
import asyncio
from backend.state.state_manager import StateManager, JarvisState, JarvisMode
from backend.event_bus import event_bus, Event, EventType

@pytest.mark.asyncio
async def test_state_manager_transitions():
    sm = StateManager()
    
    # Initial state should be IDLE, mode NORMAL
    assert sm.state == JarvisState.IDLE
    assert sm.mode == JarvisMode.NORMAL
    
    # Valid transition: IDLE -> LISTENING
    success = await sm.transition(JarvisState.LISTENING)
    assert success is True
    assert sm.state == JarvisState.LISTENING
    
    # Invalid transition: LISTENING -> SPEAKING
    success = await sm.transition(JarvisState.SPEAKING)
    assert success is False
    assert sm.state == JarvisState.LISTENING  # remains LISTENING
    
    # Valid transition: LISTENING -> THINKING
    success = await sm.transition(JarvisState.THINKING)
    assert success is True
    assert sm.state == JarvisState.THINKING

@pytest.mark.asyncio
async def test_state_manager_set_mode():
    sm = StateManager()
    
    await sm.set_mode(JarvisMode.FOCUS)
    assert sm.mode == JarvisMode.FOCUS
    
    await sm.set_mode(JarvisMode.NORMAL)
    assert sm.mode == JarvisMode.NORMAL

@pytest.mark.asyncio
async def test_state_manager_force_state():
    sm = StateManager()
    
    # Direct force state (no validation)
    await sm.force_state(JarvisState.SPEAKING)
    assert sm.state == JarvisState.SPEAKING

@pytest.mark.asyncio
async def test_state_manager_history():
    sm = StateManager()
    
    # Perform a few transitions
    await sm.transition(JarvisState.LISTENING)
    await sm.transition(JarvisState.THINKING)
    
    history = sm.get_history(limit=5)
    assert len(history) >= 2
    assert history[-2]["state"] == JarvisState.LISTENING.value
    assert history[-1]["state"] == JarvisState.THINKING.value
    assert history[-1]["previous_state"] == JarvisState.LISTENING.value

@pytest.mark.asyncio
async def test_state_manager_publishes_events():
    # Use the global state_manager singleton to test event integration
    from backend.state.state_manager import state_manager
    
    received_events = []
    async def handler(event: Event) -> None:
        received_events.append(event)
        
    event_bus.subscribe(EventType.STATE_CHANGED, handler)
    event_bus.subscribe(EventType.MODE_CHANGED, handler)
    
    # Reset/Force state to IDLE to ensure valid path
    await state_manager.force_state(JarvisState.IDLE)
    
    # Trigger transition
    await state_manager.transition(JarvisState.LISTENING, meta={"test": "meta"}, source="test_runner")
    await state_manager.set_mode(JarvisMode.OBSERVATION, source="test_runner")
    
    # Allow event_bus worker (already running or we call dispatch directly)
    # Since the global event_bus might not have its worker started in these unit tests,
    # let's publish_sync or check the event bus queue. Wait, state_manager uses `await event_bus.publish(...)`
    # so we should start the global event_bus to process the queue.
    await event_bus.start()
    await asyncio.sleep(0.1)
    
    # Unsubscribe to clean up
    event_bus.unsubscribe(EventType.STATE_CHANGED, handler)
    event_bus.unsubscribe(EventType.MODE_CHANGED, handler)
    await event_bus.stop()
    
    # Assertions
    state_event = next((e for e in received_events if e.type == EventType.STATE_CHANGED), None)
    mode_event = next((e for e in received_events if e.type == EventType.MODE_CHANGED), None)
    
    assert state_event is not None
    assert state_event.data["state"] == JarvisState.LISTENING.value
    assert state_event.data["meta"] == {"test": "meta"}
    assert state_event.source == "test_runner"
    
    assert mode_event is not None
    assert mode_event.data["mode"] == JarvisMode.OBSERVATION.value
    assert mode_event.source == "test_runner"
