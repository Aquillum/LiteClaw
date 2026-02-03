import time
import os
from datetime import datetime, timedelta
from .meta_memory import get_conscious_memory, update_conscious_memory

class ConsciousMind:
    """
    Manages the 'Conscious Memory' of LiteClaw.
    Span: 20 minutes.
    Focus: Active intents, current discussion context, and immediate goals.
    """
    MAX_EXPIRY = 20

    def __init__(self):
        self.last_sync = datetime.now()
        
    def get_active_focus(self) -> str:
        """Retrieves the current conscious focus, checking for expiry."""
        content = get_conscious_memory()
        if not content.strip():
            return "No active conscious focus. Ready for new intent."
            
        lines = content.splitlines()
        timestamp_line = lines[0] if lines else ""
        duration_line = lines[1] if len(lines) > 1 else "DURATION: 20"
        
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

    def set_active_focus(self, focus_intent: str, duration_minutes: int = 20):
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
        return f"\n### CONSCIOUS FOCUS (20-min span)\n{focus}\n"

conscious_mind = ConsciousMind()
