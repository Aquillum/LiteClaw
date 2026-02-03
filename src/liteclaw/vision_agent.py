import base64
import json
import os
import time
import sys
import uuid
import requests
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple
from collections import deque
import threading
from .config import settings

# Third-party imports
pyautogui = None
Image = None
ImageDraw = None

try:
    import pyautogui
    from PIL import Image, ImageDraw
    # Safety: Move mouse to corner to abort
    if pyautogui:
        try:
            pyautogui.FAILSAFE = True
            # Test if display is actually available
            pyautogui.size()
        except Exception as e:
            print(f"Warning: Vision libraries loaded but Display not available: {e}")
            pyautogui = None # Disable vision
except Exception as e:
    print(f"Warning: Vision features disabled. Initialization error: {e}")
    pyautogui = None
    pass

try:
    from openai import OpenAI
except ImportError:
    pass

class VisionAgent:
    def __init__(self, goal: str, session_id: str, platform: str = "whatsapp", max_steps: int = 15):
        self.goal = goal
        self.session_id = session_id
        self.platform = platform
        self.max_steps = max_steps
        self.history = []
        self.step_count = 0
        
        # Initialize Client using LiteClaw Settings (Prioritize Vision Config)
        self.model_name = settings.VISION_LLM_MODEL or settings.LLM_MODEL
        api_key = settings.VISION_LLM_API_KEY or settings.LLM_API_KEY
        base_url = settings.VISION_LLM_BASE_URL or settings.LLM_BASE_URL
        
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        # Prepare screen info
        try:
            self.screen_width, self.screen_height = pyautogui.size()
        except:
            self.screen_width, self.screen_height = (1920, 1080) # Fallback if headless/error
            
        # Ensure screenshot dir exists
        # Ensure screenshot dir exists
        self.screenshot_dir = settings.get_screenshots_dir()
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Singleton Queue Logic
        self.goal_queue = deque()
        if goal:
            self.goal_queue.append(goal)
            
        self.is_running = True
        self.current_goal = None

    def add_goal(self, goal: str):
        """Inject a new goal into the active agent."""
        if goal:
            self.goal_queue.append(goal)
            print(f"[Vision] New goal injected into queue: {goal}")

    def capture_screen(self) -> Tuple[Any, str]:
        """Captures screen, returns PIL Image and base64 string."""
        if not pyautogui or not Image:
             raise ImportError("Vision dependencies (pyautogui/Pillow) are missing.")
        
        # Adapt to screen size dynamically (refresh just in case resolution changed)
        try:
            self.screen_width, self.screen_height = pyautogui.size()
        except:
            pass
            
        screenshot = pyautogui.screenshot()
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return screenshot, img_str

    def get_system_prompt(self) -> str:
        return """
You are an advanced Vision Agent capable of controlling a computer to achieve a goal.
You will receive the current state of the screen as an image.
You must output a JSON object describing the next action to take.

### Coordinate System
- The screen uses a normalized coordinate system from 0 to 1000.
- Top-Left is (0, 0). Bottom-Right is (1000, 1000).
- When you need to click something, return its bounding box: [ymin, xmin, ymax, xmax].

### Available Actions
1. **CLICK**: Left click on an element.
   - Required fields: "bbox" (normalized [ymin, xmin, ymax, xmax])
2. **DOUBLE_CLICK**: Double left click on an element (use for opening files/folders).
   - Required fields: "bbox" (normalized [ymin, xmin, ymax, xmax])
3. **RIGHT_CLICK**: Right click on an element (use to open context menus).
   - Required fields: "bbox" (normalized [ymin, xmin, ymax, xmax])
4. **TYPE**: Type text.
   - Required fields: "text" (string to type)
5. **HOTKEY**: Press a key combination.
   - Required fields: "keys" (list of strings, e.g. ["ctrl", "c"], ["enter"], ["win"])
6. **SCROLL**: Scroll the mouse wheel.
   - Required fields: "direction" ("up" | "down"), "amount" (integer).
   - Tip: "amount" is number of mouse clicks. 1 = small step. 5 = medium.
7. **MOVE_TO**: Move the mouse without clicking.
   - Required fields: "point" ([x, y] normalized 0-1000)
8. **WAIT**: Wait for a few seconds.
   - Required fields: "duration" (float, seconds)
9. **ASK_USER**: Pause execution and ask the user for help, decision, or data.
   - Required fields: "question" (string)
10. **FINISH**: Goal is achieved or impossible.
    - Required fields: "reason" (string)

### Response Format (Strict JSON)
{
  "thought": "Brief reasoning about what to do next based on the screen.",
  "action": "CLICK" | "DOUBLE_CLICK" | "RIGHT_CLICK" | "TYPE" | "HOTKEY" | "SCROLL" | "MOVE_TO" | "WAIT" | "ASK_USER" | "FINISH",
  "bbox": [ymin, xmin, ymax, xmax],  // For CLICK, DOUBLE_CLICK, RIGHT_CLICK
  "text": "some text",               // For TYPE
  "keys": ["key1", "key2"],          // For HOTKEY
  "direction": "down",               // For SCROLL
  "amount": 3,                       // For SCROLL
  "point": [500, 500],               // For MOVE_TO
  "duration": 2.5,                   // For WAIT
  "question": "Which file?",         // For ASK_USER
  "reason": "Task done."             // For FINISH
}
Do not return markdown code blocks. Just the raw JSON string.
"""

    def parse_response(self, content: str) -> Optional[Dict[str, Any]]:
        cleaned = content.replace("```json", "").replace("```", "").strip()
        try:
            # Try standard json first
            return json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                # Try json_repair for LLM-jankiness
                from json_repair import repair_json
                repaired = repair_json(cleaned)
                return json.loads(repaired)
            except Exception as e:
                print(f"Error parsing JSON: {cleaned} (Error: {e})")
                return None

    def execute_action(self, action_data: Dict[str, Any], screenshot: Any):
        """Executes the action determined by the LLM."""
        action_type = action_data.get("action", "").upper()
        
        if action_type == "CLICK":
            bbox = action_data.get("bbox")
            if bbox:
                ymin, xmin, ymax, xmax = bbox
                center_x_norm = (xmin + xmax) / 2
                center_y_norm = (ymin + ymax) / 2
                target_x = (center_x_norm / 1000) * self.screen_width
                target_y = (center_y_norm / 1000) * self.screen_height
                
                # Visual Debug
                self.save_debug_artifact(screenshot, bbox, (target_x, target_y))
                
                pyautogui.moveTo(target_x, target_y, duration=0.5) 
                pyautogui.click()
                return f"Clicked at ({target_x}, {target_y})"
            else:
                return "Error: CLICK missing bbox"

        elif action_type == "DOUBLE_CLICK":
            bbox = action_data.get("bbox")
            if bbox:
                ymin, xmin, ymax, xmax = bbox
                center_x_norm = (xmin + xmax) / 2
                center_y_norm = (ymin + ymax) / 2
                target_x = (center_x_norm / 1000) * self.screen_width
                target_y = (center_y_norm / 1000) * self.screen_height
                
                # Visual Debug
                self.save_debug_artifact(screenshot, bbox, (target_x, target_y))
                
                pyautogui.moveTo(target_x, target_y, duration=0.5) 
                pyautogui.doubleClick()
                return f"Double-clicked at ({target_x}, {target_y})"
            else:
                return "Error: DOUBLE_CLICK missing bbox"

        elif action_type == "RIGHT_CLICK":
            bbox = action_data.get("bbox")
            if bbox:
                ymin, xmin, ymax, xmax = bbox
                center_x_norm = (xmin + xmax) / 2
                center_y_norm = (ymin + ymax) / 2
                target_x = (center_x_norm / 1000) * self.screen_width
                target_y = (center_y_norm / 1000) * self.screen_height
                
                # Visual Debug
                self.save_debug_artifact(screenshot, bbox, (target_x, target_y))
                
                pyautogui.moveTo(target_x, target_y, duration=0.5) 
                pyautogui.rightClick()
                return f"Right-clicked at ({target_x}, {target_y})"
            else:
                return "Error: RIGHT_CLICK missing bbox"

        elif action_type == "TYPE":
            text = action_data.get("text", "")
            pyautogui.write(text, interval=0.05)
            return f"Typed: '{text}'"

        elif action_type == "HOTKEY":
            keys = action_data.get("keys", [])
            pyautogui.hotkey(*keys)
            return f"Keys pressed: {keys}"

        elif action_type == "SCROLL":
            direction = action_data.get("direction", "down")
            amount = action_data.get("amount", 3)
            # Smooth scroll implementation
            # User reported 1 unit = bottom of page with previous 120 multiplier.
            # Hypothesis: On this machine, scroll value is interpreted as 'clicks', not 'units'.
            # We will use 1 as the base unit per step.
            clicks = amount
            for _ in range(clicks):
                # Using +/- 1 here assuming the OS interprets this as 1 click/notch
                scroll_cmd = -1 if direction == "down" else 1
                pyautogui.scroll(scroll_cmd)
                time.sleep(0.1) 
            
            return f"Scrolled {direction} by {clicks} steps"

        elif action_type == "MOVE_TO":
            point = action_data.get("point")
            if point:
                px, py = point
                target_x = (px / 1000) * self.screen_width
                target_y = (py / 1000) * self.screen_height
                pyautogui.moveTo(target_x, target_y, duration=0.5)
                return f"Moved cursor to ({target_x}, {target_y})"
            return "Error: MOVE_TO missing point"

        elif action_type == "WAIT":
            duration = action_data.get("duration", 1)
            time.sleep(duration)
            return f"Waited {duration}s"
        
        elif action_type == "ASK_USER":
            question = action_data.get("question", "Help needed.")
            
            # Send screenshot context to user first (so they see what the agent sees)
            self._send_screenshot_to_user(screenshot, caption=f"I need help with this: {question}")
            
            # Use browser_utils hook to wait for answer
            from .browser_utils import ask_human_for_input
            import asyncio
            
            # Helper to run async in this sync method
            def run_async(coro):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                         # This is risky in a sync call inside an unknown loop state
                         # Ideally we should use a new thread or future.
                         # For LiteClaw architecture, we use a dedicated thread helper
                         from .browser_utils import _run_async_task_in_thread
                         return _run_async_task_in_thread(coro)
                    else:
                        return loop.run_until_complete(coro)
                except Exception:
                     # Fallback
                     from .browser_utils import _run_async_task_in_thread
                     return _run_async_task_in_thread(coro)

            print(f"[Vision] Asking user: {question}")
            result = run_async(ask_human_for_input(question, self.session_id, self.platform))
            
            answer = result.extracted_content if result else "No answer."
            return f"User answered: {answer}"

        elif action_type == "FINISH":
            return "FINISH"

        return f"Unknown action: {action_type}"

    def _send_screenshot_to_user(self, image: Any, caption: str):
        """Save and send screenshot via bridge."""
        filename = f"vision_{uuid.uuid4().hex[:8]}.png"
        path = os.path.join(self.screenshot_dir, filename)
        image.save(path)
        
        try:
            from .main import WHATSAPP_BRIDGE_URL
            import requests
            
            requests.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json={
                "to": self.session_id,
                "message": f"[LiteClaw] 📸 {caption}",
                "url_or_path": path,
                "type": "image",
                "caption": caption,
                "is_media": True,
                "platform": self.platform
            })
        except Exception as e:
            print(f"Failed to send screenshot: {e}")

    def save_debug_artifact(self, image: Any, bbox: List[int], point: Tuple[int, int]):
        """Save debug artifact with bounding box and target point."""
        try:
            draw = ImageDraw.Draw(image)
            ymin, xmin, ymax, xmax = bbox
            px_xmin = (xmin / 1000) * self.screen_width
            px_xmax = (xmax / 1000) * self.screen_width
            px_ymin = (ymin / 1000) * self.screen_height
            px_ymax = (ymax / 1000) * self.screen_height
            
            draw.rectangle([px_xmin, px_ymin, px_xmax, px_ymax], outline="red", width=3)
            x, y = point
            r = 5
            draw.ellipse((x-r, y-r, x+r, y+r), fill="green", outline="green")
            
            filename = f"vision_debug_{self.step_count}.png"
            image.save(os.path.join(self.screenshot_dir, filename))
        except Exception:
            pass

    def _notify_main_session(self, message: str):
        """Send a notification message back to the main session via bridge."""
        from .main import WHATSAPP_BRIDGE_URL
        
        # Truncate if too long for messaging platforms
        if len(message) > 1500:
            message = message[:1500] + "...[truncated]"
            
        final_text = f"👁️ [Vision Agent]: {message}"
        print(f"[Vision] Sending notification to {self.session_id}: {message[:50]}...")
        
        try:
            requests.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json={
                "to": self.session_id,
                "message": final_text,
                "platform": self.platform
            })
            
            # Also attempt to persist in conversation history for the session agent
            try:
                from .memory import add_message
                add_message(self.session_id, {"role": "system", "content": final_text})
            except Exception as me:
                print(f"[Vision] Failed to update memory: {me}")
                
        except Exception as e:
            print(f"[Vision] Failed to send notification: {e}")

    def run(self):
        print(f"[Vision] Agent started. Waiting for goals...")
        
        while self.is_running:
            if not self.goal_queue:
                time.sleep(1)
                continue
                
            # Pick next goal
            self.current_goal = self.goal_queue.popleft()
            self.goal = self.current_goal # Update for system prompt context
            self.step_count = 0
            self.history = [] # Reset history for new goal? Or keep context? 
            # User said "all subagents will be a single entity", implying shared context?
            # But "injected new prompt" usually means a distinct task. 
            # Let's clean history to avoid context window explosion, but maybe keep last summary?
            # For now, clean slate per goal is safer.
            
            print(f"[Vision] 🟢 Starting goal: {self.current_goal}")
            
            current_max_steps = self.max_steps
            goal_completed = False
            
            while self.step_count < current_max_steps and not goal_completed:
                self.step_count += 1
                
                # AGI-Reflection Loop (Every 5 steps)
                checkpoint_msg = ""
                if self.step_count > 0 and self.step_count % 5 == 0:
                    print(f"[Vision] Step {self.step_count}: Entering REFLECTION phase...")
                    time.sleep(2) 
                    checkpoint_msg = (
                        f"\n\n[SYSTEM CHECKPOINT - Step {self.step_count}]"
                        f"\nSTOP. You have executed 5 steps."
                        f"\n1. REFLECT: Look at your history. Are you closer to the goal?"
                        f"\n2. ANALYZE: If you failed any steps, why?"
                        f"\n3. PLAN: What are the next 5 steps?"
                        f"\n4. ADJUST: If stuck, try a completely different approach."
                        f"\nSession limit auto-extended."
                    )
                    current_max_steps += 5
                    print(f"[Vision] Session extended. New limit: {current_max_steps}")
                
                # Check if new high-priority goal injected? (Not implementing priority yet, just FIFO)
                
                # 1. Capture
                screenshot, b64_img = self.capture_screen()
                
                # 2. Think
                try:
                    user_content_str = f"GOAL: {self.current_goal}\n\nHistory: {self.history}{checkpoint_msg}"
                    
                    messages = [
                        {"role": "system", "content": self.get_system_prompt()},
                        {
                            "role": "user", 
                            "content": [
                                {"type": "text", "text": user_content_str},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                            ]
                        }
                    ]
                    
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages
                    )
                    
                    content = response.choices[0].message.content
                    action_data = self.parse_response(content)
                    
                    if not action_data:
                        print("[Vision] Failed to parse response")
                        continue
                    
                    # 3. Act
                    result_msg = self.execute_action(action_data, screenshot)
                    
                    if result_msg == "FINISH":
                        final_reason = action_data.get('reason', 'Done')
                        print(f"[Vision] 🏁 Finished goal '{self.current_goal}': {final_reason}")
                        self._notify_main_session(f"✅ Goal Completed: {self.current_goal}\nResult: {final_reason}")
                        goal_completed = True
                        break # Break inner loop, go back to queue
                    
                    # Record History
                    summary = f"Step {self.step_count}: {action_data.get('thought')} -> {action_data.get('action')} => {result_msg}"
                    self.history.append(summary)
                    print(f"[Vision] {summary}")
                    
                    time.sleep(1)
    
                except Exception as e:
                    error_msg = f"Error executing goal '{self.current_goal}': {e}"
                    print(f"[Vision] {error_msg}")
                    self._notify_main_session(f"❌ {error_msg}")
                    goal_completed = True # Stop this goal on error
                    break
            
            if not goal_completed:
                 stop_msg = f"⚠️ Goal '{self.current_goal}' stopped (Max steps reached)."
                 print(f"[Vision] {stop_msg}")
                 self._notify_main_session(stop_msg)
        
        print("[Vision] Agent stopped.")
