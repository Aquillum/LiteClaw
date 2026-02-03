from dataclasses import dataclass
from typing import Optional
from .config import settings
import asyncio
import time
import httpx
import threading
import sys

# Define ActionResult locally since we removed browser-use
@dataclass
class ActionResult:
    extracted_content: Optional[str] = None
    error: Optional[str] = None
    is_done: bool = False

# Global storage for pending questions (session_id -> question)
_pending_questions = {}
_pending_answers = {}
_interjections = {}
_active_tasks = {} # session_id -> bool

# Platform-specific endpoint mappings
BRIDGE_SEND_ENDPOINT = "/whatsapp/send"

async def ask_human_for_input(question: str, session_id: str, platform: str = "whatsapp", timeout: int = 300) -> ActionResult:
    """
    Ask the user for input during automation.
    Stores the question and waits for response via the messaging channel.
    """
    
    # Store the question
    _pending_questions[session_id] = question
    _pending_answers[session_id] = None
    
    # Send the question to the user via the appropriate platform
    if platform == "api":
        print(f"[Input] ⚠️ API platform doesn't support push notifications. Waiting for answer via API...")
    else:
        try:
            # All platforms use the same endpoint - routing is based on "platform" field
            bridge_url = f"http://localhost:3040{BRIDGE_SEND_ENDPOINT}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(bridge_url, json={
                    "to": session_id,
                    "message": f"[LiteClaw] ⏸️ Task Paused\n\n{question}\n\n💬 Please respond to continue.",
                    "platform": platform
                }, timeout=10.0)
                
                if response.status_code == 200:
                    print(f"[Input] ✅ Sent question to user via {platform.title()}: {question[:100]}...")
                else:
                    print(f"[Input] ⚠️ Failed to send question: {response.text}")

        except Exception as e:
            print(f"[Input] ❌ Failed to send question via {platform.title()}: {e}")
            
    # Wait for answer (with timeout)
    start_time = time.time()
    while time.time() - start_time < timeout:
        if _pending_answers.get(session_id):
            answer = _pending_answers[session_id]
            # Clean up
            _pending_questions.pop(session_id, None)
            _pending_answers.pop(session_id, None)
            return ActionResult(extracted_content=f"User responded: {answer}")
        await asyncio.sleep(1)
    
    # Timeout
    _pending_questions.pop(session_id, None)
    return ActionResult(extracted_content="[TIMEOUT] No user response received", error="User did not respond in time")

def set_human_answer(session_id: str, answer: str):
    """Called externally to provide the answer to a pending question."""
    _pending_answers[session_id] = answer

def get_pending_question(session_id: str) -> str:
    """Check if there's a pending question for this session."""
    return _pending_questions.get(session_id)

def set_interjection(session_id: str, content: str):
    """Store a user message as an interjection for an active task."""
    _interjections[session_id] = content

def pop_interjection(session_id: str) -> Optional[str]:
    """Retrieve and clear an interjection for a session."""
    return _interjections.pop(session_id, None)

def set_task_active(session_id: str, is_active: bool):
    """Mark a session as having an active vision or long-running task."""
    if is_active:
        _active_tasks[session_id] = True
    else:
        _active_tasks.pop(session_id, None)

def is_task_active(session_id: str) -> bool:
    """Check if a session has an active long-running task."""
    return _active_tasks.get(session_id, False)

def _run_async_task_in_thread(coro):
    """Run an async coroutine in a dedicated thread with its own event loop."""
    result = None
    error = None
    
    def run_in_thread():
        nonlocal result, error
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            error = e
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()  # Wait for completion
    
    if error:
        raise error
    return result
