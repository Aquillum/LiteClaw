import time
import os
from datetime import datetime, timedelta
from .meta_memory import get_conscious_memory, update_conscious_memory

CONSCIOUS_SESSION_ID = "conscious-worker"

class ConsciousMind:
    """
    Manages the 'Conscious Memory' of LiteClaw.
    Span: 15 minutes.
    Focus: Active intents and immediate goals.
    This system proactively works on the 'Active Focus' in background cycles.
    """
    MAX_EXPIRY = 15

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
        print("[Conscious] 🧠 Worker system started.")

    def _loop(self):
        import time
        import random
        # Initial sleep to stagger with subconscious
        time.sleep(45)
        
        while self._running:
            # Conscious action happens every 5 to 15 minutes when there's an active focus
            wait_time = random.randint(300, 900) 
            
            # We check focus frequently to avoid sleeping through a new intent,
            # but for simplicity in this background worker, we'll follow the requested 5-15 min cadence.
            print(f"[Conscious] Next working cycle scheduled in {wait_time//60} mins {wait_time%60} secs.")
            time.sleep(wait_time)
            
            if not self._running:
                break
                
            self._trigger_work()

    def _trigger_work(self):
        """Invoke the agent to progress the active conscious focus."""
        focus = self.get_active_focus()
        if "Idle" in focus or "No active conscious focus" in focus:
            # print("[Conscious] Idle. No work to perform.")
            return
            
        # Avoid circular imports
        from .agent import LiteClawAgent
        if not self._agent:
            self._agent = LiteClawAgent()

        prompt = f"""
[CONSCIOUS WORKER - ACTIVE FOCUS]
You are currently focused on this task:
---
{focus}
---
Perform the next logical step to achieve this goal. 
If the task is complete, use the 'update_conscious' tool to set your focus to Idle and explain why.
If you need more information, or if you are stuck, state so.
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

    def set_active_focus(self, focus_intent: str, duration_minutes: int = 15):
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
