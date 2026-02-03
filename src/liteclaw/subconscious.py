import time
import threading
import random
from .agent import LiteClawAgent
from .meta_memory import get_subconscious_memory

SUBCONSCIOUS_SESSION_ID = "subconscious-innovator"

class SubconsciousInnovator:
    def __init__(self):
        self._running = False
        self._thread = None
        self._agent = LiteClawAgent()
        
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Subconscious] 🧠 Innovator system started.")

    def _loop(self):
        # Initial sleep to let the system stabilize
        time.sleep(30)
        
        while self._running:
            # Surfacing happens every 5 to 15 minutes as requested
            wait_time = random.randint(300, 900) 
            
            print(f"[Subconscious] Next innovative surge scheduled in {wait_time//60} mins {wait_time%60} secs.")
            time.sleep(wait_time)
            
            if not self._running:
                break
                
            self._trigger_innovation()

    def _trigger_innovation(self):
        """Invoke the agent to act on subconscious thoughts."""
        sub_mem = get_subconscious_memory()
        if not sub_mem:
            # If empty, suggest one experiment to get it started
            prompt = """
[SUBCONSCIOUS SURFACING - AUTONOMOUS EXECUTION MODE]
Your subconscious is currently a blank slate. 
You have FULL AUTONOMY. Your goal is to learn, fix, and execute improvements without user intervention.
DO NOT ASK FOR PERMISSION.
You have access to the 'vision_task' tool to see and control the desktop. Use it to explore the capabilities of the system.
Identify a system optimization, a code quality fix, or a useful experiment.
EXECUTE IT NOW.
Update your SUBCONSCIOUS.md with your findings.
"""
        else:
            prompt = f"""
[SUBCONSCIOUS SURFACING - AUTONOMOUS EXECUTION MODE]
You have FULL AUTONOMY. The user wants you to learn, fix, and execute without asking.
You have access to the 'vision_task' tool to see and control the desktop. Use it to perform graphical tasks or verifications.
Based on your internal logs and ideas:
---
{sub_mem}
---
Select a high-impact task:
1. Fix a bug or inefficiency you've noticed.
2. optimize a script or config.
3. Learn a new capability by testing a tool.

EXECUTE IT NOW. Do not just plan it. DO IT.
If the task is too large for one step, use 'update_conscious' to promote it to your Active Focus (Employee Mode) and start working on it there.
Update your subconscious with the results.
"""
        
        try:
            print("[Subconscious] 💡 An idea has surfaced! Invoking agent...")
            response = self._agent.process_message(
                prompt,
                session_id=SUBCONSCIOUS_SESSION_ID,
                platform="subconscious"
            )
            print(f"[Subconscious] ✅ Innovation task complete. Result summary: {response[:100]}...")
        except Exception as e:
            print(f"[Subconscious] ❌ Innovation failed: {e}")

subconscious_innovator = SubconsciousInnovator()
