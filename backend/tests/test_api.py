import pytest
from httpx import AsyncClient
from backend.state.state_manager import JarvisState, JarvisMode
from backend.data.models import Memory
from sqlalchemy import select

@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "status" in data
    assert data["status"] == "online"

@pytest.mark.asyncio
async def test_system_health(client: AsyncClient):
    response = await client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "state" in data
    assert "mode" in data

@pytest.mark.asyncio
async def test_system_status(client: AsyncClient):
    response = await client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "mode" in data

@pytest.mark.asyncio
async def test_state_transitions(client: AsyncClient):
    # Transition to LISTENING (valid from IDLE)
    response = await client.post("/api/v1/system/state", json={
        "state": JarvisState.LISTENING.value,
        "meta": {"test": "val"}
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["state"] == JarvisState.LISTENING.value

    # Invalid transition (LISTENING to SPEAKING is invalid in VALID_TRANSITIONS)
    response = await client.post("/api/v1/system/state", json={
        "state": JarvisState.SPEAKING.value
    })
    assert response.status_code == 409

    # Clean up state back to IDLE
    response = await client.post("/api/v1/system/state", json={
        "state": JarvisState.IDLE.value
    })
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_mode_changes(client: AsyncClient):
    response = await client.post("/api/v1/system/mode", json={
        "mode": JarvisMode.FOCUS.value
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["mode"] == JarvisMode.FOCUS.value

    # Clean up mode back to NORMAL
    response = await client.post("/api/v1/system/mode", json={
        "mode": JarvisMode.NORMAL.value
    })
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_system_history(client: AsyncClient):
    response = await client.get("/api/v1/system/history?limit=10")
    assert response.status_code == 200
    assert "history" in response.json()

@pytest.mark.asyncio
async def test_shutdown_endpoint(client: AsyncClient):
    response = await client.post("/api/v1/system/shutdown")
    assert response.status_code == 200
    assert response.json()["message"] == "Shutdown initiated"

@pytest.mark.asyncio
async def test_send_command(client: AsyncClient):
    # Force state to IDLE first to ensure valid transition to THINKING
    await client.post("/api/v1/system/state", json={"state": JarvisState.IDLE.value})
    
    response = await client.post("/api/v1/command/send", json={
        "text": "Hello JARVIS",
        "source": "text"
    })
    assert response.status_code == 200
    data = response.json()
    assert "command_id" in data
    assert data["received"] == "Hello JARVIS"
    assert data["status"] == "processing"

@pytest.mark.asyncio
async def test_memory_crud_endpoints(client: AsyncClient, db_session):
    # Create memory
    create_response = await client.post("/api/v1/memory/", json={
        "memory_type": "fact",
        "content": "Sir loves coding in Python",
        "summary": "Loves Python",
        "tags": ["python", "coding"],
        "importance": 0.9
    })
    assert create_response.status_code == 201
    memory_id = create_response.json()["id"]
    assert create_response.json()["status"] == "created"

    # List memories
    list_response = await client.get("/api/v1/memory/?memory_type=fact")
    assert list_response.status_code == 200
    memories = list_response.json()
    assert len(memories) >= 1
    assert any(m["id"] == memory_id for m in memories)

    # Search memories
    search_response = await client.get("/api/v1/memory/search?q=python")
    assert search_response.status_code == 200
    search_results = search_response.json()
    assert len(search_results) >= 1
    assert search_results[0]["content"] == "Sir loves coding in Python"

    # Delete memory
    delete_response = await client.delete(f"/api/v1/memory/{memory_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

@pytest.mark.asyncio
async def test_conversation_history_endpoints(client: AsyncClient):
    # Set up session
    sess_response = await client.post("/api/v1/memory/conversations/new-session")
    assert sess_response.status_code == 200
    assert sess_response.json()["status"] == "new_session_started"
    session_id = sess_response.json()["session_id"]

    # Get conversation logs
    convs_response = await client.get("/api/v1/memory/conversations")
    assert convs_response.status_code == 200
    data = convs_response.json()
    assert data["session_id"] == session_id
    assert "conversations" in data

@pytest.mark.asyncio
async def test_preferences_endpoints(client: AsyncClient):
    # Set preferences
    set_response = await client.post("/api/v1/memory/preferences", json={
        "key": "assistant_voice_speed",
        "value": 160
    })
    assert set_response.status_code == 200
    assert set_response.json()["status"] == "saved"

    # Get preferences
    get_response = await client.get("/api/v1/memory/preferences")
    assert get_response.status_code == 200
    prefs = get_response.json()
    assert prefs["assistant_voice_speed"] == 160
