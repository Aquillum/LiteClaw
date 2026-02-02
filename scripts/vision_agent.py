import base64
import json
import os
import re
import time
import sys
import argparse
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple, Union

# Third-party imports
try:
    import pyautogui
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: 'pyautogui' and 'pillow' are required. Install: pip install pyautogui pillow")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Error: 'openai' is required. Install: pip install openai")
    sys.exit(1)

# --- Configuration ---
API_BASE = "https://openrouter.ai/api/v1"
# Default key from previous context or env
DEFAULT_API_KEY = ""
API_KEY = os.getenv("LLM_API_KEY", DEFAULT_API_KEY)
MODEL_NAME = "google/gemini-3-flash-preview"

# Safety: Move mouse to corner to abort
pyautogui.FAILSAFE = True

class VisionAgent:
    def __init__(self, goal: str, max_steps: int = 10):
        self.goal = goal
        self.max_steps = max_steps
        self.history = []
        self.step_count = 0
        self.client = OpenAI(base_url=API_BASE, api_key=API_KEY)
        self.screen_width, self.screen_height = pyautogui.size()
        
        print(f"Vision Agent Initialized.")
        print(f"Goal: {self.goal}")
        print(f"Screen Resolution: {self.screen_width}x{self.screen_height}")

    def capture_screen(self) -> Tuple[Image.Image, str]:
        """Captures screen, returns PIL Image and base64 string."""
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
1. **CLICK**: Click on an element.
   - Required fields: "bbox" (normalized [ymin, xmin, ymax, xmax])
2. **TYPE**: Type text.
   - Required fields: "text" (string to type)
3. **HOTKEY**: Press a key combination.
   - Required fields: "keys" (list of strings, e.g. ["ctrl", "c"], ["enter"], ["win"])
4. **WAIT**: Wait for a few seconds (e.g., for page load).
   - Required fields: "duration" (float, seconds)
5. **FINISH**: Goal is achieved or impossible.
   - Required fields: "reason" (string)

### Response Format (Strict JSON)
{
  "thought": "Brief reasoning about what to do next based on the screen.",
  "action": "CLICK" | "TYPE" | "HOTKEY" | "WAIT" | "FINISH",
  "bbox": [ymin, xmin, ymax, xmax],  // Only for CLICK
  "text": "some text",               // Only for TYPE
  "keys": ["key1", "key2"],          // Only for HOTKEY
  "duration": 2.5                    // Only for WAIT
  "reason": "Task done."             // Only for FINISH
}
Do not return markdown code blocks. Just the raw JSON string.
"""

    def parse_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Parses LLM response, handling potential formatting issues."""
        # Cleanup markdown if present
        cleaned = content.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError:
            print(f"Error parsing JSON: {cleaned}")
            # simple retry or fallback logic could go here
            return None

    def execute_action(self, action_data: Dict[str, Any], screenshot: Image.Image):
        """Executes the action determined by the LLM."""
        action_type = action_data.get("action", "").upper()
        
        if action_type == "CLICK":
            bbox = action_data.get("bbox")
            if bbox:
                ymin, xmin, ymax, xmax = bbox
                # Convert normalized to pixels
                # Gemini bbox is [ymin, xmin, ymax, xmax] -> 0-1000
                
                center_x_norm = (xmin + xmax) / 2
                center_y_norm = (ymin + ymax) / 2
                
                target_x = int((center_x_norm / 1000) * self.screen_width)
                target_y = int((center_y_norm / 1000) * self.screen_height)
                
                print(f"  > CLICK at ({target_x}, {target_y}) (Source bbox: {bbox})")
                
                # Visual Debug
                self.save_debug_artifact(screenshot, bbox, (target_x, target_y))
                
                # Move and Click
                # Smooth move to look more human-like
                pyautogui.moveTo(target_x, target_y, duration=0.5) 
                pyautogui.click()
            else:
                print("  > CLICK action missing 'bbox'.")

        elif action_type == "TYPE":
            text = action_data.get("text", "")
            print(f"  > TYPE: '{text}'")
            pyautogui.write(text, interval=0.05)

        elif action_type == "HOTKEY":
            keys = action_data.get("keys", [])
            print(f"  > HOTKEY: {keys}")
            pyautogui.hotkey(*keys)

        elif action_type == "WAIT":
            duration = action_data.get("duration", 1)
            print(f"  > WAIT: {duration}s")
            time.sleep(duration)
            
        elif action_type == "FINISH":
            print(f"  > FINISHED: {action_data.get('reason')}")
            return True # Signal to stop

        else:
            print(f"  > Unknown action: {action_type}")
            
        return False

    def save_debug_artifact(self, image: Image.Image, bbox: List[int], point: Tuple[int, int]):
        """Saves an image with the intended action visualization."""
        try:
            draw = ImageDraw.Draw(image)
            ymin, xmin, ymax, xmax = bbox
            
            # Convert bbox to pixels for drawing
            px_xmin = (xmin / 1000) * self.screen_width
            px_xmax = (xmax / 1000) * self.screen_width
            px_ymin = (ymin / 1000) * self.screen_height
            px_ymax = (ymax / 1000) * self.screen_height
            
            draw.rectangle([px_xmin, px_ymin, px_xmax, px_ymax], outline="red", width=3)
            
            # Draw point
            x, y = point
            r = 5
            draw.ellipse((x-r, y-r, x+r, y+r), fill="green", outline="green")
            
            filename = f"vision_debug_step_{self.step_count}.png"
            image.save(filename)
            print(f"    (Debug image saved to {filename})")
        except Exception as e:
            print(f"    (Failed to save debug image: {e})")

    def run(self):
        while self.step_count < self.max_steps:
            self.step_count += 1
            print(f"\n--- Step {self.step_count} ---")
            
            # 1. Capture
            screenshot, b64_img = self.capture_screen()
            
            # 2. Think
            print("Thinking...")
            try:
                messages = [
                    {"role": "system", "content": self.get_system_prompt()},
                    # We could include history here if we wanted multi-turn context
                    # For now, let's just send the goal + current screenshot 
                    # (Stateless-ish, but sufficient for many linear tasks)
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": f"GOAL: {self.goal}\n\nHistory of actions: {self.history}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                        ]
                    }
                ]
                
                response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    # response_format={"type": "json_object"} # Gemini 2.0 Flash supports this ideally
                )
                
                content = response.choices[0].message.content
                print(f"Plan: {content}")
                
                action_data = self.parse_response(content)
                if not action_data:
                    print("Failed to interpret LLM response. Retrying step...")
                    continue
                
                # 3. Act
                is_finished = self.execute_action(action_data, screenshot)
                
                # Record History
                summary = f"Step {self.step_count}: {action_data.get('thought')} -> {action_data.get('action')}"
                self.history.append(summary)
                
                if is_finished:
                    print("\nTask Completed Successfully.")
                    break
                    
                # Short pause between steps to let UI settle
                time.sleep(1)

            except Exception as e:
                print(f"Error during step execution: {e}")
                break
        
        if self.step_count >= self.max_steps:
            print("\nMax steps reached. Stopping.")

def main():
    parser = argparse.ArgumentParser(description="AI Vision Agent")
    parser.add_argument("goal", type=str, help="The task you want the agent to perform.", nargs="?")
    args = parser.parse_args()

    goal = args.goal
    if not goal:
        goal = input("Enter your goal: ")
        
    agent = VisionAgent(goal)
    
    # Give user a moment to switch windows if needed
    print("\nStarting in 3 seconds... Switch to the target window!")
    time.sleep(3)
    
    agent.run()

if __name__ == "__main__":
    main()
