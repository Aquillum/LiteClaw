from browser_use import Agent, Browser, ChatOpenAI, Tools, ActionResult
from .config import settings
from .meta_memory import get_soul_memory
import asyncio
import os
import traceback
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Global storage for pending questions (session_id -> question)
_pending_questions = {}
_pending_answers = {}

# Global persistent browser instance for reuse
# NOTE: Disabled due to browser-use internal event bus issues (QueueShutDown)
# Each task now creates a fresh browser to avoid stale state
_global_browser = None
_browser_lock = threading.Lock()

# Registry of active browsers for termination [session_id] -> [Browser, ...]
_active_browsers = {}
_active_browsers_lock = threading.Lock()

# Platform-specific endpoint mappings
# NOTE: The bridge uses a SINGLE endpoint (/whatsapp/send) for all platforms
# and routes based on the "platform" field in the JSON body
BRIDGE_SEND_ENDPOINT = "/whatsapp/send"

def register_browser(session_id: str, browser: Browser):
    """Register an active browser instance."""
    with _active_browsers_lock:
        if session_id not in _active_browsers:
            _active_browsers[session_id] = []
        _active_browsers[session_id].append(browser)

def unregister_browser(session_id: str, browser: Browser):
    """Unregister a browser instance."""
    with _active_browsers_lock:
        if session_id in _active_browsers:
            if browser in _active_browsers[session_id]:
                _active_browsers[session_id].remove(browser)
            if not _active_browsers[session_id]:
                del _active_browsers[session_id]

async def kill_browsers_for_session(session_id: str):
    """Forcefully close all browsers for a session."""
    browsers_to_kill = []
    with _active_browsers_lock:
        if session_id in _active_browsers:
            browsers_to_kill = list(_active_browsers[session_id])
    
    if not browsers_to_kill:
        return "No active browsers found for this session."
    
    count = 0
    for browser in browsers_to_kill:
        try:
            print(f"[Browser] 🛑 Force killing browser for session {session_id}...")
            await browser.close()
            count += 1
        except Exception as e:
            print(f"[Browser] ⚠️ Error killing browser: {e}")
            
    return f"Terminated {count} active browser instance(s)."

def create_browser(headless: bool = True, disable_security: bool = True, allowed_domains: list = None, executable_path: str = None) -> Browser:
    """Create a fresh browser instance for each task to avoid stale event bus."""
    print(f"[Browser] Creating new browser instance (Headless={headless})...")
    browser = Browser(
        headless=headless,
        disable_security=disable_security,
        allowed_domains=allowed_domains,
        executable_path=executable_path,
        storage_state='./auth.json',
        keep_alive=False  # Don't keep alive to avoid stale event bus
    )
    print(f"[Browser] ✅ Browser created")
    return browser


async def ask_human_for_input(question: str, session_id: str, platform: str = "whatsapp", timeout: int = 300) -> ActionResult:
    """
    Ask the user for input during browser automation.
    Stores the question and waits for response via the messaging channel.
    
    Args:
        question: The question to ask
        session_id: Current session ID (for routing the question)
        platform: The platform to send the question through (whatsapp, telegram, api, etc.)
        timeout: Max seconds to wait for response (default: 5 minutes)
    
    Returns:
        ActionResult with the user's answer
    """
    import httpx
    
    # Store the question
    _pending_questions[session_id] = question
    _pending_answers[session_id] = None
    
    # Send the question to the user via the appropriate platform
    # Skip sending for API platform (it doesn't have a push notification mechanism)
    if platform == "api":
        print(f"[Browser] ⚠️ API platform doesn't support push notifications. Waiting for answer via API...")
    else:
        try:
            # All platforms use the same endpoint - routing is based on "platform" field
            bridge_url = f"http://localhost:3040{BRIDGE_SEND_ENDPOINT}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(bridge_url, json={
                    "to": session_id,
                    # CRITICAL: Include [LiteClaw] tag to prevent main agent from processing this message again
                    "message": f"[LiteClaw] ⏸️ Browser Task Paused\n\n{question}\n\n💬 Please respond to continue.",
                    "platform": platform  # This determines where the bridge routes the message
                }, timeout=10.0)
                
                if response.status_code == 200:
                    print(f"[Browser] ✅ Sent question to user via {platform.title()}: {question[:100]}...")
                else:
                    # Show full error response for debugging
                    try:
                        error_data = response.json()
                        print(f"[Browser] ⚠️ {platform.title()} error ({response.status_code}):")
                        print(f"  Error: {error_data.get('error', 'Unknown')}")
                        print(f"  Type: {error_data.get('errorType', 'N/A')}")
                        if error_data.get('errorStack'):
                            print(f"  Stack: {error_data.get('errorStack')[:200]}...")
                    except:
                        print(f"[Browser] ⚠️ {platform.title()} response code {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"[Browser] ❌ Failed to send question via {platform.title()}: {e}")
            import traceback
            traceback.print_exc()
    
    # Wait for answer (with timeout)
    start_time = time.time()
    while time.time() - start_time < timeout:
        if _pending_answers.get(session_id):
            answer = _pending_answers[session_id]
            # Clean up
            _pending_questions.pop(session_id, None)
            _pending_answers.pop(session_id, None)
            return ActionResult(extracted_content=f"User responded: {answer}")
        await asyncio.sleep(1)
    
    # Timeout
    _pending_questions.pop(session_id, None)
    return ActionResult(extracted_content="[TIMEOUT] No user response received", error="User did not respond in time")

def set_human_answer(session_id: str, answer: str):
    """Called externally to provide the answer to a pending question."""
    _pending_answers[session_id] = answer

def get_pending_question(session_id: str) -> str:
    """Check if there's a pending question for this session."""
    return _pending_questions.get(session_id)

def get_browser_llm():
    """Get the configured LLM for browser-use tasks."""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )

async def _run_browser_task(task_description: str, session_id: str, platform: str = "whatsapp", headless: bool = True, disable_security: bool = True, allowed_domains: list[str] = None, executable_path: str = None, keep_open: bool = False):
    """Internal async runner for browser-use with verbose logging and smart context."""
    llm = get_browser_llm()
    
    # 1. Fetch User Context (SOUL)
    user_context = get_soul_memory()
    
    # 2. Construct "Smart Prompt"
    final_task = f"""
    MATCH THIS GOAL: {task_description}

    ## CONTEXT (User Profile & Preferences)
    Use this information to fill forms, answer questions, or make decisions. 
    If a field is missing here, make a reasonable guess or leave it blank if optional.
    {user_context}

    ## INSTRUCTIONS
    1. **Efficiency & Stop**: Complete the goal with the minimum number of steps. STOP immediately as soon as the goal is achieved. Do not explore further.
    2. **Plan & Optimize**: Analyze the page layout quickly. If a solution seems suboptimal or slow, find a better path.
    3. **Resilience & Recovery**: If an error occurs (popups, slow loads, missing elements), analyze why and attempt ONE alternate "better" solution.
    4. **Extraction**: Ensure data is actually visible (scroll if needed) before extracting, but don't over-scroll.
    5. **Verify**: Briefly confirm success (e.g., check for a confirmation message) then finish.
    
    ## CRITICAL: WAITING FOR USER INPUT
    **NEVER complete the task if you need input from the user!**
    If the task requires user input (text to enter, choices to make, data to provide):
    - DO NOT mark the task as done with a message like "waiting for your input" or "the page is ready"
    - INSTEAD: Use the `ask_human` action IMMEDIATELY to request the needed information
    - Examples:
      * If asked to open a QR generator and wait for text: Use `ask_human("What text would you like me to convert to a QR code?")`
      * If asked to fill a form but missing data: Use `ask_human("I need the following information: [specific fields]")`
      * If you reach a step requiring user decision: Use `ask_human("Which option should I select? I see: [list options]")`
    - WAIT for the user's response before continuing
    - Only mark the task as done when you have COMPLETED the actual action with the user's input
    
    ## CRITICAL: PAYMENT HANDLING
    **NEVER STOP AT PAYMENT/CHECKOUT SCREENS!**
    If you reach any payment page, checkout screen, or are prompted for payment information:
    - DO NOT mark the task as done
    - DO NOT stop with a message like "You are now at the stage where you can select payment method"
    - INSTEAD: Use the `ask_human` action immediately to request payment details from the user
    - Ask questions like:
      * "Which payment method would you like to use? I can see these options: [list available options]"
      * "Please provide your UPI ID" (if UPI is selected)
      * "Please provide your card number, expiry, and CVV" (if card payment is selected)
      * "Should I proceed with [specific wallet/method]?"
    - Wait for the user's response
    - Complete the ENTIRE payment process including entering details and confirming the order
    - The task is ONLY complete when you see an order confirmation, success message, or order ID
    - If the user doesn't want to complete payment, they will explicitly tell you to stop
    
    ## SCREENSHOTS
    If the user asks you to "send a screenshot", "share the screen", "show me the page", or similar:
    - Use the `send_screenshot` action with an appropriate caption
    - This will automatically take a screenshot and send it to the user
    - You can use this to show results, confirmations, or any visual outcome
    - Example: `send_screenshot("Here is your generated QR code")`
    """

    # Resolve executable path for common browser names
    if executable_path:
        ep_lower = executable_path.lower()
        if ep_lower == "brave":
            brave_paths = [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
            ]
            for p in brave_paths:
                if os.path.exists(p):
                    executable_path = p
                    break
        elif ep_lower == "chrome":
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            for p in chrome_paths:
                if os.path.exists(p):
                    executable_path = p
                    break

    # Create fresh browser for this task (avoids stale event bus issues)
    browser = create_browser(
        headless=headless,
        disable_security=disable_security,
        allowed_domains=allowed_domains,
        executable_path=executable_path
    )
    
    # Register browser for potential kill command
    register_browser(session_id, browser)
    
    # Setup human-in-the-loop tools
    tools = Tools()
    
    @tools.action('Ask human for help with a question (REQUIRED for payment info, credentials, or when you need user choices/clarification). Use this especially when reaching payment/checkout screens.')
    async def ask_human(question: str) -> ActionResult:
        return await ask_human_for_input(question, session_id, platform=platform)
    
    @tools.action('Take a screenshot of the current browser page and send it to the user. Use this when the user asks to see the page, share a screenshot, or when you want to show them the result.')
    async def send_screenshot(caption: str = "Here is the screenshot") -> ActionResult:
        """Take screenshot of current page and send to user."""
        import httpx
        import base64
        import uuid
        
        try:
            # Get current page from browser
            page = await browser.get_current_page()
            
            if not page:
                return ActionResult(extracted_content="Error: No browser page available", error="No page to screenshot")
            
            # Take screenshot - browser-use wraps Playwright, try different approaches
            print(f"[Browser] 📸 Taking screenshot...")
            screenshot_bytes = None
            
            try:
                # Try 1: Direct call (browser-use sometimes supports this)
                screenshot_bytes = await page.screenshot()
            except TypeError:
                try:
                    # Try 2: Access underlying Playwright page if available
                    if hasattr(page, '_page'):
                        screenshot_bytes = await page._page.screenshot()
                    elif hasattr(page, 'page'):
                        screenshot_bytes = await page.page.screenshot()
                    else:
                        # Try 3: Call with path to temp file
                        import tempfile
                        temp_path = os.path.join(tempfile.gettempdir(), f"screenshot_{uuid.uuid4().hex[:8]}.png")
                        await page.screenshot(path=temp_path)
                        with open(temp_path, 'rb') as f:
                            screenshot_bytes = f.read()
                        os.remove(temp_path)
                except Exception as inner_e:
                    print(f"[Browser] Screenshot fallback also failed: {inner_e}")
                    return ActionResult(extracted_content=f"Screenshot capture failed: {str(inner_e)}", error=str(inner_e))
            
            if not screenshot_bytes:
                return ActionResult(extracted_content="Error: Could not capture screenshot", error="Empty screenshot")
            
            # Save to screenshots directory in work dir
            screenshot_filename = f"browser_screenshot_{uuid.uuid4().hex[:8]}.png"
            # Use configured work directory, ensure it exists
            settings.ensure_work_dirs()
            screenshot_path = os.path.join(settings.get_screenshots_dir(), screenshot_filename)
            
            # Handle both base64 string and bytes
            if isinstance(screenshot_bytes, str):
                with open(screenshot_path, 'wb') as f:
                    f.write(base64.b64decode(screenshot_bytes))
            else:
                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot_bytes)
            
            print(f"[Browser] 📸 Screenshot saved to: {screenshot_path}")
            
            # Send screenshot to user via their messaging platform
            bridge_url = f"http://localhost:3040{BRIDGE_SEND_ENDPOINT}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(bridge_url, json={
                    "to": session_id,
                    "message": f"[LiteClaw] 📸 {caption}",
                    "url_or_path": screenshot_path,
                    "type": "image",
                    "caption": f"[LiteClaw] {caption}",
                    "is_media": True,
                    "platform": platform
                })
                
                if response.status_code == 200:
                    print(f"[Browser] ✅ Screenshot sent to user via {platform.title()}")
                    return ActionResult(extracted_content=f"✅ Screenshot ALREADY SENT to user with caption: '{caption}'. DO NOT send it again - the user has received it.")
                else:
                    print(f"[Browser] ⚠️ Failed to send screenshot: {response.status_code}")
                    return ActionResult(extracted_content=f"Screenshot saved to {screenshot_path} but failed to send: {response.status_code}. You may use send_media to retry.")
                    
        except Exception as e:
            print(f"[Browser] ❌ Screenshot error: {e}")
            import traceback
            traceback.print_exc()
            return ActionResult(extracted_content=f"Screenshot error: {str(e)}", error=str(e))
    
    agent = Agent(
        task=final_task,
        llm=llm,
        browser=browser,
        tools=tools  # Enable human interaction and screenshot
    )
    
    print(f"\n[Browser] Starting Smart Task (Headless={headless}, SecurityDisable={disable_security}, Exec={executable_path})")
    print(f"[Browser] Goal: {task_description}")
    print(f"[Browser] Using fresh browser instance for this task (KeepOpen={keep_open})")
    
    try:
        result = await agent.run()
        final_result = result.final_result()
        print(f"[Browser] ✅ Task completed. Result length: {len(str(final_result)) if final_result else 0}")
        
        # Append clear message about screenshots to prevent duplication
        if final_result and ("screenshot" in str(final_result).lower() or "sent" in str(final_result).lower()):
            final_result = f"{final_result}\n\n[IMPORTANT: Any screenshots taken during this task were ALREADY SENT to the user. Do NOT call send_media to send them again.]"
        
        return final_result
    except Exception as e:
        print(f"\n[Browser] CRITICAL ERROR during execution: {e}")
        traceback.print_exc()
        return f"Browser Error: {str(e)}"
    finally:
        # Clean up browser after task
        try:
            if not keep_open:
                unregister_browser(session_id, browser)
                await browser.close()
                print(f"[Browser] 🧹 Browser closed after task")
            else:
                print(f"[Browser] ⏸️ Browser kept open by request (Kill via 'kill_sub_agent' or 'shutdown')")
                # Ensure it's still registered for later killing
        except Exception as close_err:
            print(f"[Browser] ⚠️ Browser close warning: {close_err}")

def _run_async_task_in_thread(coro):
    """Run an async coroutine in a dedicated thread with its own event loop."""
    result = None
    error = None
    
    def run_in_thread():
        nonlocal result, error
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            error = e
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()  # Wait for completion
    
    if error:
        raise error
    return result

def run_browser_task(task: str, session_id: str, platform: str = "whatsapp", show_browser: bool = False, disable_security: bool = True, allowed_domains: list[str] = None, executable_path: str = None, keep_open: bool = False) -> str:
    """Synchronous wrapper to run the browser task."""
    print(f"[Browser] sync wrapper: Starting for platform={platform}, keep_open={keep_open}")
    try:
        headless = not show_browser
        
        print(f"[Browser] sync wrapper: Running async task in dedicated thread...")
        
        # Use dedicated thread approach to avoid event loop conflicts
        result = _run_async_task_in_thread(
            _run_browser_task(
                task,
                session_id=session_id,
                platform=platform,
                headless=headless, 
                disable_security=disable_security, 
                allowed_domains=allowed_domains,
                executable_path=executable_path,
                keep_open=keep_open
            )
        )
        
        print(f"[Browser] sync wrapper: ✅ Got result, returning to agent (len={len(str(result)) if result else 0})")
        return result
    except Exception as e:
        print(f"\n[Browser] Wrapper Error: {e}")
        traceback.print_exc()
        return f"Browser Task Error: {str(e)}"
