import threading
import uuid
import time
import httpx
import asyncio
from typing import Dict, List, Optional
from .agent import LiteClawAgent

class SubAgent:
    def __init__(self, sub_agent_id: str, session_id: str, name: str):
        self.sub_agent_id = sub_agent_id
        self.session_id = session_id # This refers to the main user session (e.g. 'whatsapp')
        self.name = name
        self.status = "idle"  # idle, working, completed, failed
        self.last_result = None
        self.task_history = []
        self._thread = None
        self._agent = LiteClawAgent() 

    def run_task(self, task: str):
        self.status = "working"
        self.task_history.append({"task": task, "start_time": time.time()})
        
        def _task_wrapper():
            try:
                # 1. Execute task
                result = self._agent.process_message(
                    f"BACKGROUND TASK: {task}. NOTE: You are the sub-agent '{self.name}'. Work in project root 'd:\\openclaw_lite'.", 
                    session_id=f"sub_{self.sub_agent_id}"
                )
                self.last_result = result
                self.status = "completed"
                self.task_history[-1]["end_time"] = time.time()
                self.task_history[-1]["result"] = result
                
                # 2. Notify User regarding completion
                self._notify_completion(result)
                
            except Exception as e:
                self.status = "failed"
                self.last_result = f"Error: {str(e)}"
                self.task_history[-1]["error"] = str(e)
                self._notify_completion(f"❌ Sub-Agent '{self.name}' failed: {str(e)}")

        self._thread = threading.Thread(target=_task_wrapper)
        self._thread.start()

    async def _notify_completion_async(self, message: str):
        """Notification bridge back to the main user session."""
        from .main import WHATSAPP_BRIDGE_URL
        final_text = f"✅ [Sub-Agent '{self.name}' Complete]:\n{message}"
        print(f"[Sub-Agent] Sending completion to {self.session_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json={
                    "to": self.session_id,
                    "message": f"[LiteClaw] {final_text}"
                })
        except Exception as e:
            print(f"[Sub-Agent] Failed to send completion notify: {e}")

    def _notify_completion(self, message: str):
        """Run the async notification in a safe way."""
        try:
            asyncio.run(self._notify_completion_async(message))
        except RuntimeError:
            # If we're already in a loop, create a task (though in a thread this shouldn't happen)
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._notify_completion_async(message))
        except Exception as e:
            print(f"[Sub-Agent] Notify Error: {e}")

class SubAgentManager:
    def __init__(self, max_per_session: int = 5):
        self.sessions: Dict[str, List[SubAgent]] = {}
        self.max_per_session = max_per_session

    def get_or_create_sub_agent(self, session_id: str, name: str) -> Optional[SubAgent]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        for sa in self.sessions[session_id]:
            if sa.name == name:
                return sa
        
        if len(self.sessions[session_id]) < self.max_per_session:
            sub_agent_id = str(uuid.uuid4())[:8]
            new_sa = SubAgent(sub_agent_id, session_id, name)
            self.sessions[session_id].append(new_sa)
            return new_sa
        return None

    def delegate_task(self, session_id: str, sub_agent_name: str, task: str) -> str:
        sa = self.get_or_create_sub_agent(session_id, sub_agent_name)
        if not sa:
            return f"Error: Maximum of {self.max_per_session} sub-agents reached."
        
        if sa.status == "working":
            return f"Error: Sub-agent '{sub_agent_name}' is busy."
        
        sa.run_task(task)
        return f"Task delegated to '{sub_agent_name}'. It will notify you here when done."

    def list_sub_agents(self, session_id: str) -> List[Dict]:
        if session_id not in self.sessions:
            return []
        return [
            {
                "name": sa.name,
                "id": sa.sub_agent_id,
                "status": sa.status,
                "last_result": sa.last_result
            } for sa in self.sessions[session_id]
        ]

sub_agent_manager = SubAgentManager()
