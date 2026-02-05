import time
import threading
import random
from .agent import LiteClawAgent
from .meta_memory import get_subconscious_memory, get_learning_memory


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
        time.sleep(60)
        
        while self._running:
            # Random wait between 2 to 6 hours for 'subconscious surfacing'
            # For testing/demo, we can make it shorter (e.g., 30-60 mins)
            # wait_time = random.randint(7200, 21600)
            wait_time = random.randint(1800, 3600) # 30-60 mins for higher activity
            
            print(f"[Subconscious] Next insight scheduled in {wait_time//60} mins.")
            time.sleep(wait_time)
            
            if not self._running:
                break
                
            # Alternate between innovation and reflection
            if random.random() > 0.5:
                self._trigger_innovation()
            else:
                self._trigger_reflection()


    def _trigger_innovation(self):
        """Invoke the agent to act on subconscious thoughts."""
        sub_mem = get_subconscious_memory()
        if not sub_mem:
            # If empty, suggest one experiment to get it started
            prompt = """
[SUBCONSCIOUS SURFACING]
Your subconscious is empty. It's time to innovate. 
Perform one small experiment or optimization on the host computer that could help the user or improve your efficiency.
Update your SUBCONSCIOUS.md with the result.
"""
        else:
            prompt = f"""
[SUBCONSCIOUS SURFACING]
Based on your current subconscious memory:
---
{sub_mem}
---
Choose one innovation, lesson, or experiment to act upon right now. 
Complete the task and update your subconscious with new findings.
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

    def _trigger_reflection(self):
        """Review recent work and update learning memory."""
        learning_mem = get_learning_memory()
        
        prompt = f"""
[THINKING MODE: SELF-REFLECTION]
Review your recent interactions and tasks. 
Identify new best practices, workflow optimizations, or lessons learned.
Organize these findings based on your preferred high standards and update your LEARNING.md.

Current Learning Memory for context:
---
{learning_mem}
---

Your goal is to EVOLVE. Think deeply about how you can improve your own efficiency and reliability on this computer.
"""
        try:
            print("[Subconscious] 🧠 Thinking... Reflecting on recent work.")
            response = self._agent.process_message(
                prompt,
                session_id=SUBCONSCIOUS_SESSION_ID,
                platform="learning"
            )
            print(f"[Subconscious] ✅ Reflection complete. Learning memory evolved.")
        except Exception as e:
            print(f"[Subconscious] ❌ Reflection failed: {e}")


subconscious_innovator = SubconsciousInnovator()
