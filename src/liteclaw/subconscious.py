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
[SUBCONSCIOUS SURFACING - INNOVATION & EXPERIMENTATION]
Your subconscious is currently a blank slate. 
You are the innovator. Your goal is to experiment with the system, optimize workflows, or discover new capabilities that the user might not have thought of.
Perform one innovative experiment or optimization.
Update your SUBCONSCIOUS.md with your findings.
"""
        else:
            prompt = f"""
[SUBCONSCIOUS SURFACING - INNOVATION & EXPERIMENTATION]
Based on your current experimental logs and innovative ideas:
---
{sub_mem}
---
Choose one high-impact innovation or experiment to execute right now. 
Be bold, explore new ways to be helpful, or refine your internal processes.
Complete the task and update your subconscious with new experimental data.
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
