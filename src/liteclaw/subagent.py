import threading
import uuid
import time
import httpx
import asyncio
from typing import Dict, List, Optional
from .agent import LiteClawAgent

# Platform-specific endpoint mappings
# NOTE: The bridge uses a SINGLE endpoint (/whatsapp/send) for all platforms
# and routes based on the "platform" field in the JSON body
BRIDGE_SEND_ENDPOINT = "/whatsapp/send"

class SubAgent:
    def __init__(self, sub_agent_id: str, session_id: str, name: str, platform: str = "whatsapp"):
        self.sub_agent_id = sub_agent_id
        self.session_id = session_id # This refers to the main user session
        self.name = name
        self.platform = platform  # Track the platform for notifications
        self.status = "idle"  # idle, working, completed, failed
        self.last_result = None
        self.task_history = []
        self.message_queue = []
        self._thread = None
        self._agent = LiteClawAgent()

    def run_task(self, task: str):
        self.status = "working"
        self.task_history.append({"task": task, "start_time": time.time()})

        def _task_wrapper():
            try:
                # 1. Execute task
                # CRITICAL: Use self.session_id (the parent session)
                # and self.platform so browser questions route correctly
                result = self._agent.process_message(
                    f"BACKGROUND TASK: {task}. NOTE: You are the sub-agent '{self.name}'. Work in project root 'd:\\\\openclaw_lite'.",
                    session_id=self.session_id,  # Use parent session
                    platform=self.platform  # Use parent platform for correct routing
                )
                
                # Check if we were terminated while working
                if self.status == "terminated":
                    print(f"[Sub-Agent] '{self.name}' finished work but was terminated. disregarding result.")
                    return

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

    def receive_message(self, sender: str, text: str):
        """Receive a message from another agent or session."""
        msg = f"FROM {sender}: {text}"
        self.message_queue.append({"sender": sender, "text": text, "time": time.time()})
        print(f"[Sub-Agent] '{self.name}' received message from {sender}: {text[:50]}...")
        
        # Inject into agent history if possible
        from .memory import add_message
        add_message(f"subagent-{self.sub_agent_id}", {"role": "user", "content": f"[INCOMING MESSAGE] {msg}"})

    async def _notify_completion_async(self, message: str):
        """Notification bridge back to the main user session via the correct platform."""
        from .main import WHATSAPP_BRIDGE_URL

        # Truncate if too long
        if len(message) > 1500:
            message = message[:1500] + "...[truncated]"

        final_text = f"✅ [Sub-Agent '{self.name}' Complete]:\n{message}"
        print(f"[Sub-Agent] Sending completion to {self.session_id} via {self.platform.title()}")

        # Skip for API platform (no push notifications)
        if self.platform == "api":
            print(f"[Sub-Agent] API platform - completion message logged only: {final_text[:100]}...")
            return

        try:
            # All platforms use the same endpoint - routing is based on "platform" field
            bridge_url = f"{WHATSAPP_BRIDGE_URL}{BRIDGE_SEND_ENDPOINT}"

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(bridge_url, json={
                    "to": self.session_id,
                    "message": f"[LiteClaw] {final_text}",
                    "platform": self.platform
                })
                if response.status_code == 200:
                    print(f"[Sub-Agent] ✅ Completion notification sent successfully via {self.platform.title()}")
                else:
                    print(f"[Sub-Agent] ⚠️ Notification response ({self.platform.title()}): {response.status_code}")
        except Exception as e:
            print(f"[Sub-Agent] ❌ Failed to send completion notify via {self.platform.title()}: {e}")

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

    def get_or_create_sub_agent(self, session_id: str, name: str, platform: str = "whatsapp") -> Optional[SubAgent]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        for sa in self.sessions[session_id]:
            if sa.name == name:
                # Update platform in case it changed
                sa.platform = platform
                return sa

        if len(self.sessions[session_id]) < self.max_per_session:
            sub_agent_id = str(uuid.uuid4())[:8]
            new_sa = SubAgent(sub_agent_id, session_id, name, platform=platform)
            self.sessions[session_id].append(new_sa)
            return new_sa
        return None

    def delegate_task(self, session_id: str, sub_agent_name: str, task: str, platform: str = "whatsapp") -> str:
        sa = self.get_or_create_sub_agent(session_id, sub_agent_name, platform=platform)
        if not sa:
            return f"Error: Maximum of {self.max_per_session} sub-agents reached."

        if sa.status == "working":
            return f"Error: Sub-agent '{sub_agent_name}' is busy."

        sa.run_task(task)
        return f"Task delegated to '{sub_agent_name}'. It will notify you via {platform.title()} when done."

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
    
        return f"Error: Sub-agent '{sub_agent_name}' not found."

    def kill_sub_agent(self, session_id: str, sub_agent_name: str) -> str:
        """Gracefully terminate a sub-agent by name."""
        if session_id not in self.sessions:
            return f"Error: No sub-agents found for session {session_id}."
        
        for sa in self.sessions[session_id]:
            if sa.name == sub_agent_name:
                if sa.status == "working":
                    sa.status = "terminated"
                    sa.last_result = "Task was terminated by user request."
                    
                    # Kill associated browser session(s)
                    try:
                        from .browser_utils import kill_browsers_for_session
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # We are in a running loop, create a task (fire and forget)
                                asyncio.ensure_future(kill_browsers_for_session(session_id))
                            else:
                                loop.run_until_complete(kill_browsers_for_session(session_id))
                        except Exception:
                            # Fallback if get_event_loop fails or other issues
                            asyncio.run(kill_browsers_for_session(session_id))
                            
                        return f"✅ Sub-agent '{sub_agent_name}' terminated and browser sessions killed."
                    except Exception as e:
                        return f"✅ Sub-agent '{sub_agent_name}' terminated, but browser kill failed: {e}"
                else:
                    return f"Sub-agent '{sub_agent_name}' is not currently working (status: {sa.status})."
        
        return f"Error: Sub-agent '{sub_agent_name}' not found."

    def message_sub_agent(self, session_id: str, sub_agent_name: str, sender: str, text: str) -> str:
        """Send a message to a specific sub-agent."""
        if session_id not in self.sessions:
            return f"Error: No sub-agents found for session {session_id}."
        
        for sa in self.sessions[session_id]:
            if sa.name == sub_agent_name:
                sa.receive_message(sender, text)
                return f"Message delivered to '{sub_agent_name}'."
        
        # Check if target is 'vision' (special handling)
        if sub_agent_name.lower() == "vision":
            from .agent import GLOBAL_VISION_AGENT
            if GLOBAL_VISION_AGENT and GLOBAL_VISION_AGENT.is_running:
                GLOBAL_VISION_AGENT.add_goal(f"[MESSAGE FROM {sender}]: {text}")
                return "Vision Agent received the message as a priority goal."
        
        return f"Error: Sub-agent '{sub_agent_name}' not found."
    
    def kill_all_sub_agents(self, session_id: str) -> str:
        """Terminate all sub-agents for a session."""
        if session_id not in self.sessions:
            return "No active sub-agents."
        
        killed = 0
        for sa in self.sessions[session_id]:
            if sa.status == "working":
                sa.status = "terminated"
                sa.last_result = "Task was terminated by user request."
                killed += 1
        
        if killed > 0:
            # Kill associated browser session(s)
            try:
                from .browser_utils import kill_browsers_for_session
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(kill_browsers_for_session(session_id))
                    else:
                        loop.run_until_complete(kill_browsers_for_session(session_id))
                except Exception:
                    asyncio.run(kill_browsers_for_session(session_id))
                return f"✅ Terminated {killed} sub-agent(s) and their browsers."
            except Exception as e:
                return f"✅ Terminated {killed} sub-agent(s), but browser kill failed: {e}"
        
        return "No working sub-agents found to terminate."

sub_agent_manager = SubAgentManager()
