import pytest
import asyncio
from backend.event_bus.bus import EventBus, Event, EventType

@pytest.mark.asyncio
async def test_event_bus_subscribe_publish():
    bus = EventBus()
    received_events = []

    async def sample_handler(event: Event) -> None:
        received_events.append(event)

    # Subscribe to SYSTEM_BOOT
    bus.subscribe(EventType.SYSTEM_BOOT, sample_handler)

    # Publish SYSTEM_BOOT
    test_event = Event(type=EventType.SYSTEM_BOOT, data={"status": "test"}, priority="HIGH")
    await bus.publish(test_event)

    # Start event bus worker manually and process queue
    await bus.start()
    
    # Give the background worker a tiny bit of time to execute
    await asyncio.sleep(0.1)
    
    # Verify handler received the event
    assert len(received_events) == 1
    assert received_events[0].type == EventType.SYSTEM_BOOT
    assert received_events[0].data["status"] == "test"
    assert received_events[0].priority == "HIGH"

    await bus.stop()

@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    bus = EventBus()
    received_events = []

    async def sample_handler(event: Event) -> None:
        received_events.append(event)

    bus.subscribe(EventType.SYSTEM_BOOT, sample_handler)
    bus.unsubscribe(EventType.SYSTEM_BOOT, sample_handler)

    test_event = Event(type=EventType.SYSTEM_BOOT, data={"status": "test"})
    await bus.publish(test_event)

    await bus.start()
    await asyncio.sleep(0.1)

    # Verify no events were received because we unsubscribed
    assert len(received_events) == 0

    await bus.stop()

@pytest.mark.asyncio
async def test_event_bus_priority_dispatch():
    bus = EventBus()
    dispatched_order = []

    async def handler(event: Event) -> None:
        dispatched_order.append(event.priority)

    bus.subscribe(EventType.SYSTEM_BOOT, handler)

    # Publish a Low priority event, then a High priority event
    # We load them into the queue before starting the worker to verify priority order
    event_low = Event(type=EventType.SYSTEM_BOOT, priority="LOW")
    event_high = Event(type=EventType.SYSTEM_BOOT, priority="HIGH")
    event_med = Event(type=EventType.SYSTEM_BOOT, priority="MEDIUM")

    await bus.publish(event_low)
    await bus.publish(event_med)
    await bus.publish(event_high)

    # Start the worker. Since HIGH priority is mapped to 0, MEDIUM to 1, and LOW to 2,
    # the PriorityQueue should pop them in order: HIGH, MEDIUM, LOW.
    await bus.start()
    await asyncio.sleep(0.1)

    assert dispatched_order == ["HIGH", "MEDIUM", "LOW"]

    await bus.stop()

