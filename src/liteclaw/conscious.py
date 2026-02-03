import time
import os
from datetime import datetime, timedelta
from .meta_memory import get_conscious_memory, update_conscious_memory

CONSCIOUS_SESSION_ID = "conscious-worker"

class ConsciousMind:
    """
    Manages the 'Conscious Memory' of LiteClaw.
    Span: 10 minutes (Employee Mode).
    Focus: High precision. Immediate tasks. Low time span.
    This system proactively works on the 'Active Focus' in rapid, high-focus background cycles.
    """
    MAX_EXPIRY = 10

    def __init__(self):
        self.last_sync = datetime.now()
        self._running = False
        self._thread = None
        self._agent = None # Deferred init

    def start(self):
        if self._running:
            return
        self._running = True
        import threading
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Conscious] 🧠 Employee System started.")

    def _loop(self):
        import time
        import random
        # Initial sleep to stagger
        time.sleep(30)
        
        while self._running:
            # High precision mode: Work happens every 2 to 5 minutes
            wait_time = random.randint(120, 300) 
            
            print(f"[Conscious] Next high-precision task scheduled in {wait_time//60} mins {wait_time%60} secs.")
            time.sleep(wait_time)
            
            if not self._running:
                break
                
            self._trigger_work()

    def _trigger_work(self):
        # Avoid circular imports
        from .agent import LiteClawAgent
        if not self._agent:
            self._agent = LiteClawAgent()

        focus = self.get_active_focus()
        if "Idle" in focus or "No active conscious focus" in focus:
            print(f"[Conscious] 💤 Idle detected. Initiating Autonomous Job Search...")
            prompt = """
[CONSCIOUS WORKER - AUTONOMOUS JOB SEARCH]
You are currently IDLE. The user has mandated: "Learn, fix, and execute without asking."
Passivity is NOT allowed.
You have full access to the 'vision_task' tool to control the computer contextually. Use it to verify data, inspect the screen, or perform actions.

Your Goal:
1. Scan your 'Subconscious Memory' (using tools) or check system health.
2. Identify a high-value task that fits a 10-minute sprint.
3. IMMEDIATELY set your Active Focus using 'update_conscious'.
4. Perform the first step of that task.

DO NOT ask for permission. Find work and DO IT.
"""
        else:
            prompt = f"""
[CONSCIOUS WORKER - EMPLOYEE MODE]
You are currently in specific, high-precision "Employee Mode".
Your time span is short (max 10 mins). You must be efficient and precise.
You have full access to the 'vision_task' tool to control the computer contextually. Use it to verify data, inspect the screen, or perform actions.

CURRENT ACTIVE FOCUS:
---
{focus}
---
Perform the next IMMEDIATE, PRECISE step to forward this specific goal.
Do not hallucinate scope. Stick to the immediate task.
If the task is complete, use the 'update_conscious' tool to set your focus to Idle.
"""
        
        try:
            print(f"[Conscious] 🔨 Working on focus: {focus[:50]}...")
            response = self._agent.process_message(
                prompt,
                session_id=CONSCIOUS_SESSION_ID,
                platform="conscious"
            )
            print(f"[Conscious] ✅ Work step complete.")
        except Exception as e:
            print(f"[Conscious] ❌ Work cycle failed: {e}")

    def get_active_focus(self) -> str:
        """Retrieves the current conscious focus, checking for expiry."""
        content = get_conscious_memory()
        if not content.strip():
            return "No active conscious focus. Ready for new intent."
            
        lines = content.splitlines()
        timestamp_line = lines[0] if lines else ""
        duration_line = lines[1] if len(lines) > 1 else f"DURATION: {self.MAX_EXPIRY}"
        
        if timestamp_line.startswith("TIMESTAMP:"):
            try:
                ts_str = timestamp_line.replace("TIMESTAMP:", "").strip()
                last_update = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                
                # Parse duration
                duration_mins = self.MAX_EXPIRY
                if duration_line.startswith("DURATION:"):
                    try:
                        duration_mins = int(duration_line.replace("DURATION:", "").strip())
                        duration_mins = min(duration_mins, self.MAX_EXPIRY) # Cap it
                    except:
                        pass

                if datetime.now() - last_update > timedelta(minutes=duration_mins):
                    # Conscious memory expired
                    self.clear_focus(f"Memory expired ({duration_mins}min span reached).")
                    return "Previous conscious focus expired. Ready for new intent."
            except Exception:
                pass
                
        return content

    def set_active_focus(self, focus_intent: str, duration_minutes: int = 10):
        """Sets a new conscious focus with a current timestamp and duration."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        duration = min(int(duration_minutes), self.MAX_EXPIRY)
        content = f"TIMESTAMP: {timestamp}\nDURATION: {duration}\n\nACTIVE FOCUS:\n{focus_intent}"
        update_conscious_memory(content)
        print(f"[Conscious] 🧠 New focus set for {duration} mins: {focus_intent[:50]}...")

    def clear_focus(self, reason: str = "Task completed"):
        """Clears the conscious memory."""
        update_conscious_memory(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nACTIVE FOCUS:\nIdle. Reason: {reason}")
        print(f"[Conscious] 💤 Memory cleared: {reason}")

    def get_prompt_snippet(self) -> str:
        """Returns a system-ready snippet of conscious awareness."""
        focus = self.get_active_focus()
        return f"\n### CONSCIOUS FOCUS ({self.MAX_EXPIRY}-min span)\n{focus}\n"

conscious_mind = ConsciousMind()
