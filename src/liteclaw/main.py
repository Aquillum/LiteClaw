from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import os
from typing import Optional
import uuid
import httpx
from .agent import process_message, stream_process_message
from .memory import create_session
from .config import settings
import traceback
from .scheduler import cron_manager

app = FastAPI(title="LiteClaw Backend")

@app.on_event("startup")
async def startup_event():
    cron_manager.start()
    
    # Start Heartbeat Monitor
    from .heartbeat import heartbeat
    heartbeat.start()

class CreateSessionRequest(BaseModel):
    session_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    stream: bool = False
    session_id: Optional[str] = "default"

class CreateJobRequest(BaseModel):
    name: str
    schedule_type: str # cron, interval, webhook
    schedule_value: str
    task: str

@app.post("/cron/jobs")
async def create_cron_job(req: CreateJobRequest):
    job_id = cron_manager.create_job(req.name, req.schedule_type, req.schedule_value, req.task)
    return {"status": "created", "job_id": job_id}

@app.get("/cron/jobs")
async def list_cron_jobs():
    return cron_manager.list_jobs()

@app.delete("/cron/jobs/{job_id}")
async def delete_cron_job(job_id: str):
    cron_manager.delete_job(job_id)
    return {"status": "deleted"}

@app.post("/cron/webhook/{job_id}")
async def trigger_cron_webhook(job_id: str):
    triggered = await cron_manager.trigger_job(job_id)
    if not triggered:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "triggered"}

# WhatsApp Bridge Integration
WHATSAPP_BRIDGE_URL = "http://localhost:3040"

# Simple in-memory de-duplication for WhatsApp messages
PROCESSED_MESSAGES = set()

@app.post("/whatsapp/incoming")
async def handle_whatsapp_incoming(request: Request):
    # Parsing manually to handle 'from' key safely
    data = await request.json()
    
    # De-duplication check
    msg_id = data.get('message_id')
    if msg_id:
        if msg_id in PROCESSED_MESSAGES:
            return {"status": "ignored_duplicate"}
        PROCESSED_MESSAGES.add(msg_id)
        # Prevent memory growth
        if len(PROCESSED_MESSAGES) > 1000:
            PROCESSED_MESSAGES.clear()

    sender = data.get('from') # This is the session key (remote user ID)
    message = data.get('body')
    sender_name = data.get('senderName', 'Unknown')
    from_me = data.get('fromMe', False)
    platform = data.get('platform', 'whatsapp') # Default to whatsapp if missing
    
    if not sender or not message:
        return {"status": "ignored"}
    
    prefix = "[Self]" if from_me else "[Incoming]"
    print(f"[{platform.title()}] {prefix} {sender_name} ({sender}): {message}")
    
    # Loop Prevention
    if "[LiteClaw]" in message:
        return {"status": "ignored_loop_prevent"}
    
    # Authorization Check: 
    # For WhatsApp, we check the number. For Telegram/Slack, we might be open or need a new config.
    # For now, we only enforcing strict check on WhatsApp to match existing logic.
    if platform == "whatsapp":
        allowed_list = settings.WHATSAPP_ALLOWED_NUMBERS
        if allowed_list:
            is_authorized = any(num in sender for num in allowed_list)
            if not is_authorized:
                return {"status": "ignored_unauthorized"}
    
    # 1. Create/Get Session
    # Use the specific sender ID as the session_id so sub-agents can notify back
    session_id = sender 
    create_session(session_id)

    # CHECK FOR RESET COMMAND
    if message.strip().lower() == "/reset":
        from .memory import reset_session
        reset_session(session_id)
        print(f"[{platform.title()}] Session '{session_id}' RESET by user.")
        
        # Send confirmation via the correct platform
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json={
                    "to": sender,
                    "message": "[LiteClaw] 🔄 Session reset. Context cleared.",
                    "platform": platform  # Route to correct platform
                })
            except Exception:
                pass
        return {"status": "reset"}

    # 2. Store Message & Handle Logic
    # Include sender context so the AI knows who it's talking to within the shared session
    context_message = f"[{sender_name} ({sender})]: {message}"

    # PRIORITY CHECK #1: Is this a response to a browser question?
    # This must come BEFORE the from_me check so browser answers work regardless of sender
    from .browser_utils import get_pending_question, set_human_answer
    pending_q = get_pending_question(session_id)
    
    if pending_q:
        # User is responding to a browser automation question
        set_human_answer(session_id, message)
        
        # Send confirmation (only if not from self to avoid double messages)
        if not from_me:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json={
                        "to": sender,
                        "message": f"[LiteClaw] ✅ Got it! Continuing browser task with your answer: \"{message}\"",
                        "platform": platform
                    })
                except:
                    pass
        else:
            print(f"[Browser] ✅ Received answer to pending question: {message}")
        
        return {"status": "browser_question_answered"}

    # PRIORITY CHECK #2: Loop Prevention for LiteClaw messages
    if "[LiteClaw]" in message:
        return {"status": "ignored_bot_loop"}

    # All other messages continue to agent processing
    # (Browser answers and loop prevention already handled above)

    async def typing_loop():
        """Keep sending typing status while AI is thinking."""
        async with httpx.AsyncClient() as client:
            while not stop_typing_event.is_set():
                try:
                    await client.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/typing", json={"to": sender, "platform": platform})
                except:
                    pass
                await asyncio.sleep(4) # Telegram typing expires every 5s

    import asyncio
    stop_typing_event = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop())

    try:
        # CRITICAL: Use run_in_threadpool to avoid blocking the main async loop with the sync process_message
        from fastapi.concurrency import run_in_threadpool
        response_text = await run_in_threadpool(process_message, context_message, session_id=session_id, platform=platform)
        
        # Stop the typing indicator
        stop_typing_event.set()
        await typing_task

        final_reply = f"[LiteClaw] {response_text}"
        
        # 4. Send Reply via Node Bridge
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json={
                    "to": sender,
                    "message": final_reply,
                    "platform": platform
                })
                # Turn off typing (explicitly for WhatsApp)
                if platform == 'whatsapp':
                    await client.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/stop-typing", json={"to": sender, "platform": platform})
            except Exception as e:
                print(f"[{platform.title()}] Failed to send reply: {e}")

    except Exception as e:
        print(f"[WhatsApp] CRITICAL ERROR processing message: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

    return {"status": "processed"}

@app.post("/session/create")
def create_session_endpoint(request: CreateSessionRequest):
    sid = request.session_id
    if not sid:
        sid = str(uuid.uuid4())
    elif " " in sid:
        raise HTTPException(status_code=400, detail="Session ID cannot contain spaces.")
    
    if create_session(sid):
        return {"session_id": sid, "status": "created"}
    else:
        # If it exists, we just return it, effectively "joining" it (or could raise error)
        return {"session_id": sid, "status": "exists"}

@app.get("/sessions/list")
def list_sessions_endpoint():
    from .memory import list_sessions
    return list_sessions()

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if request.stream:
        return StreamingResponse(
            stream_process_message(request.message, request.session_id, platform="api"),
            media_type="text/plain"
        )
    else:
        response = process_message(request.message, request.session_id, platform="api")
        return {"response": response}

@app.get("/")
def read_root():
    index_path = os.path.join(os.getcwd(), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "LiteClaw Backend Running"}
