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
        self.screenshot_dir = settings.get_screenshots_dir()
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Singleton Queue Logic
        self.goal_queue = deque()
        self.feedback_queue = deque() # Real-time corrections
        if goal:
            self.goal_queue.append(goal)
            
        self.is_running = True
        self.current_goal = None

    def add_goal(self, goal: str):
        """Inject a new goal into the active agent."""
        if goal:
            self.goal_queue.append(goal)
            print(f"[Vision] New goal injected into queue: {goal}")

    def add_feedback(self, feedback: str):
        """Inject an immediate correction or feedback into the current task."""
        if feedback:
            self.feedback_queue.append(feedback)
            print(f"[Vision] Feedback/Correction received: {feedback}")

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
        
        # Handle Retina Scaling (macOS)
        if screenshot.size != (self.screen_width, self.screen_height):
            screenshot = screenshot.resize((self.screen_width, self.screen_height), Image.Resampling.LANCZOS)

        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return screenshot, img_str

    def get_system_prompt(self) -> str:
        return """
You are an advanced Vision Agent capable of controlling a computer to achieve a goal.
You operate in a **Plan-Work-Loop** cycle:
1. **PLAN**: Analyze the screen and create a list of logical steps to achieve the goal or the next milestone.
2. **WORK**: Execute the planned steps sequentially.
3. **LOOP**: Re-evaluate the screen after the plan is completed or if a step requires dynamic feedback.

### Coordinate System
- The screen uses a normalized coordinate system from 0 to 1000.
- Top-Left is (0, 0). Bottom-Right is (1000, 1000).
- When you need to click something, return its bounding box: [ymin, xmin, ymax, xmax].

### Detailed Planning
- When creating a plan, describe what you intend to do in the next 1-5 actions.
- This prevents duplicated work and ensures logical flow (e.g. click search bar -> type text -> press enter).

### Available Actions
1. **CLICK**: Left click on an element.
2. **DOUBLE_CLICK**: Double left click.
3. **RIGHT_CLICK**: Right click.
4. **TYPE**: Type text.
5. **HOTKEY**: Press a key combination (e.g. ["ctrl", "v"]).
6. **SCROLL**: Scroll ("up" | "down", amount).
7. **WAIT**: Wait for seconds.
8. **ASK_USER**: Ask the user for help.
9. **FINISH**: Goal succeeded or failed.

### Response Format (Strict JSON)
You must return a **list of action objects**. Even if it's just one action, it must be in a list.
[
  {
    "thought": "I see the icon, I should click it.",
    "action": "CLICK",
    "bbox": [ymin, xmin, ymax, xmax]
  },
  {
    "thought": "Now that the window is open, I will type the search query.",
    "action": "TYPE",
    "text": "my search"
  }
]

Do characters like ```json etc are forbidden. Just the raw JSON array.
"""

    def parse_response(self, content: str) -> List[Dict[str, Any]]:
        cleaned = content.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(cleaned)
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            try:
                from json_repair import repair_json
                repaired = repair_json(cleaned)
                data = json.loads(repaired)
                return data if isinstance(data, list) else [data]
            except Exception as e:
                print(f"Error parsing JSON: {cleaned} (Error: {e})")
                return []

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
            clicks = amount
            for _ in range(clicks):
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
            self._send_screenshot_to_user(screenshot, caption=f"I need help with this: {question}")
            
            from .browser_utils import ask_human_for_input
            import asyncio
            
            def run_async(coro):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                         from .browser_utils import _run_async_task_in_thread
                         return _run_async_task_in_thread(coro)
                    else:
                        return loop.run_until_complete(coro)
                except Exception:
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
            self.goal = self.current_goal 
            self.step_count = 0
            self.history = [] 
            
            print(f"[Vision] 🟢 Starting goal: {self.current_goal}")
            
            current_max_steps = self.max_steps
            goal_completed = False
            
            while self.step_count < current_max_steps and not goal_completed:
                # 1. Capture Screen
                screenshot, b64_img = self.capture_screen()
                
                # Check for Feedback
                feedback_msg = ""
                if self.feedback_queue:
                    feedback_msg = "\n[USER CORRECTION]: " + "\n- ".join(list(self.feedback_queue))
                    self.feedback_queue.clear()

                # 2. Think & Plan (Call LLM)
                try:
                    user_content_str = f"GOAL: {self.current_goal}\n\nHistory: {self.history}\n{feedback_msg}"
                    print(f"[Vision] Thinking about the next plan...")
                    
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
                    plan = self.parse_response(content)
                    
                    if not plan:
                        print("[Vision] Failed to generate plan. Retrying...")
                        time.sleep(2)
                        continue
                    
                    # 3. Work (Execute Plan)
                    print(f"[Vision] 📋 Executing plan of {len(plan)} actions...")
                    for action_data in plan:
                        if self.step_count >= current_max_steps:
                            break
                        
                        if isinstance(action_data, list):
                            action_data = action_data[0]
                            
                        self.step_count += 1
                        
                        # Execute
                        result_msg = self.execute_action(action_data, screenshot)
                        
                        if result_msg == "FINISH":
                            final_reason = action_data.get('reason', 'Done')
                            print(f"[Vision] 🏁 Finished: {final_reason}")
                            self._notify_main_session(f"✅ Goal Completed: {self.current_goal}\nResult: {final_reason}")
                            goal_completed = True
                            break
                        
                        # Record
                        summary = f"Step {self.step_count}: {action_data.get('thought')} -> {action_data.get('action')} => {result_msg}"
                        self.history.append(summary)
                        print(f"[Vision] {summary}")
                        
                        time.sleep(1.5)
                        
                    if goal_completed:
                        break
                    
                    # End of plan cycle
                    print(f"[Vision] Plan cycle complete. Re-evaluating...")
    
                except Exception as e:
                    error_msg = f"Error in vision cycle: {e}"
                    print(f"[Vision] {error_msg}")
                    self._notify_main_session(f"❌ {error_msg}")
                    goal_completed = True
                    break
            
            if not goal_completed:
                 stop_msg = f"⚠️ Goal '{self.current_goal}' stopped (Max steps reached)."
                 print(f"[Vision] {stop_msg}")
                 self._notify_main_session(stop_msg)
        
        print("[Vision] Agent stopped.")
