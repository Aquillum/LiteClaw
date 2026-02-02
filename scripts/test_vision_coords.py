import base64
import json
import os
import re
import time
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple

# Third-party imports
try:
    import pyautogui
    from PIL import ImageDraw
except ImportError:
    print("Error: 'pyautogui' (and Pillow) is required. Install it using: pip install pyautogui")
    if __name__ == "__main__":
        exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Error: 'openai' is required. Install it using: pip install openai")
    if __name__ == "__main__":
        exit(1)

# Configuration
# Using Gemini 2.0 Flash via OpenRouter (or compatible endpoint)
API_BASE = "https://openrouter.ai/api/v1"
API_KEY = os.getenv("LLM_API_KEY", "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") 
MODEL_NAME = "google/gemini-3-flash-preview" 

def take_screenshot() -> Tuple[Any, str, Tuple[int, int]]:
    """
    Captures the primary monitor and returns:
    1. The PIL Image object
    2. Base64 encoded string
    3. Screen dimensions (width, height)
    """
    print("Taking screenshot...")
    screenshot = pyautogui.screenshot()
    width, height = screenshot.size
    
    # Save to buffer
    buffered = BytesIO()
    screenshot.save(buffered, format="PNG")
    
    # Encode to base64
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return screenshot, img_str, (width, height)

def parse_gemini_bbox(response_text: str) -> Optional[List[int]]:
    """
    Parses [ymin, xmin, ymax, xmax] from text.
    Gemini typically outputs: [ymin, xmin, ymax, xmax]
    """
    # Look for a list pattern like [123, 456, 789, 1000]
    match = re.search(r'\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]', response_text)
    if match:
        return [int(g) for g in match.groups()]
    return None

def find_coordinates(
    element_name: str, 
    client: OpenAI, 
    base64_image: str, 
    screen_size: Tuple[int, int]
) -> Optional[Dict[str, Any]]:
    """
    Asks Gemini to find the coordinates of a specific element.
    """
    screen_w, screen_h = screen_size
    
    # Gemini 2.0 Flash Prompt Strategy
    # Using normalized coordinates (0-1000)
    prompt_text = (
        f"Find the '{element_name}' button and return its bounding box. "
        "Return the response as a list [ymin, xmin, ymax, xmax] with values normalized from 0 to 1000. "
        "Do not output markdown."
    )

    print(f"Sending request to {MODEL_NAME} to find '{element_name}'...")
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
        )

        content = response.choices[0].message.content
        print(f"Raw Response: {content}")
        
        bbox = parse_gemini_bbox(content)
        
        if bbox:
            ymin, xmin, ymax, xmax = bbox
            
            # Convert normalized (0-1000) to actual pixels
            # Gemini typically does [y, x, y, x]
            
            # Calculate center point
            center_x_norm = (xmin + xmax) / 2
            center_y_norm = (ymin + ymax) / 2
            
            actual_x = int((center_x_norm / 1000) * screen_w)
            actual_y = int((center_y_norm / 1000) * screen_h)
            
            # Calculate actual bbox for reference
            act_xmin = int((xmin / 1000) * screen_w)
            act_ymin = int((ymin / 1000) * screen_h)
            act_xmax = int((xmax / 1000) * screen_w)
            act_ymax = int((ymax / 1000) * screen_h)

            return {
                "label": element_name,
                "point": [actual_x, actual_y],
                "bbox": [act_xmin, act_ymin, act_xmax, act_ymax],
                "raw_bbox": bbox
            }
        else:
            print("Failed to parse bounding box from response.")
            return None

    except Exception as e:
        print(f"Error calling LLM: {e}")
        return None

def main():
    # Initialize OpenAI client
    # Using OpenRouter Base URL and Key from env
    client = OpenAI(
        base_url=API_BASE,
        api_key=API_KEY
    )

    target = "File"
    print(f"Attempting to find coordinates for: {target}")
    
    # 1. Take Screenshot
    pil_image, b64_str, screen_dims = take_screenshot()
    
    # 2. Get Coordinates
    result = find_coordinates(target, client, b64_str, screen_dims)
    
    if result:
        print("\nSUCCESS!")
        print(f"Element: {result.get('label')}")
        point = result.get('point')
        bbox = result.get('bbox')
        
        print(f"Calculated Screen Coordinates: X={point[0]}, Y={point[1]}")
        print(f"Screen BBox: {bbox}")
        
        # 3. Validated & Draw Logic
        try:
            draw = ImageDraw.Draw(pil_image)
            
            # Draw Rectangle (Red, width 3)
            # bbox is [xmin, ymin, xmax, ymax]
            draw.rectangle(bbox, outline="red", width=5)
            
            # Draw Center Point (Green circle)
            radius = 5
            x, y = point
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="green", outline="green")
            
            # Save Debug Image
            output_filename = "vision_debug.png"
            pil_image.save(output_filename)
            print(f"Saved debug image with mask to: {os.path.abspath(output_filename)}")
            
        except Exception as e:
            print(f"Error drawing on image: {e}")

    else:
        print("\nFAILURE: Could not find coordinates.")

if __name__ == "__main__":
    main()
