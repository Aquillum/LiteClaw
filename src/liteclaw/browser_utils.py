from browser_use import Agent, Browser, ChatOpenAI
from .config import settings
from .meta_memory import get_soul_memory
import asyncio
import os
import traceback

def get_browser_llm():
    """Get the configured LLM for browser-use tasks."""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )

async def _run_browser_task(task_description: str, headless: bool = True, disable_security: bool = True, allowed_domains: list[str] = None, executable_path: str = None):
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

    # Configure browser
    browser = Browser(
        headless=headless,
        disable_security=disable_security,
        allowed_domains=allowed_domains,
        executable_path=executable_path
    )
    
    agent = Agent(
        task=final_task,
        llm=llm,
        browser=browser
    )
    
    print(f"\n[Browser] Starting Smart Task (Headless={headless}, SecurityDisable={disable_security}, Exec={executable_path})")
    print(f"[Browser] Goal: {task_description}")
    
    try:
        result = await agent.run()
        print(f"[Browser] Task completed.\n")
        return result.final_result()
    except Exception as e:
        print(f"\n[Browser] CRITICAL ERROR during execution: {e}")
        traceback.print_exc()
        return f"Browser Error: {str(e)}"
    finally:
        # Ensure browser is closed
        try:
            await browser.close()
        except:
            pass

def run_browser_task(task: str, show_browser: bool = False, disable_security: bool = True, allowed_domains: list[str] = None, executable_path: str = None) -> str:
    """Synchronous wrapper to run the browser task."""
    try:
        headless = not show_browser
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            
        return asyncio.run(_run_browser_task(
            task, 
            headless=headless, 
            disable_security=disable_security, 
            allowed_domains=allowed_domains,
            executable_path=executable_path
        ))
    except Exception as e:
        print(f"\n[Browser] Wrapper Setup Error: {e}")
        traceback.print_exc()
        return f"Browser Task Error: {str(e)}"
