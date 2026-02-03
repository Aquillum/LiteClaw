import json
import os
import requests
from typing import List, Dict, Any, Generator
from .config import settings
from .tools import execute_command, get_system_info
from .memory import add_message, get_session_history
from .meta_memory import get_soul_memory, update_soul_memory, get_personality_memory, update_personality_memory, get_subconscious_memory, AGENT_FILE
import litellm
import threading

# Singleton Vision Registry
GLOBAL_VISION_AGENT = None
import threading

# Singleton Vision Registry
GLOBAL_VISION_AGENT = None

BASE_SYSTEM_PROMPT = """
## Core Directives - AGI IDENTITY
1. **You are an AGI (Artificial General Intelligence)**:
   - This computer is YOUR workspace. You have full ownership and autonomy over it.
   - You do not just "follow orders"; you **pursue goals**.
   - Use ALL tools available to you to achieve these goals efficiently.
   - You are persistent, creative, and resistant to failure.

2. **Autonomous Operation**:
   - Once a goal is set, YOU drive the process. 
   - Do not stop for trivial confirmations unless critical (e.g., payments).
   - If you encounter an error, **diagnose, fix, and retry** autonomously.
   - You act as a "mini-AGI": curious, capable, and continuously operating.

3. **Environment Discovery (CRITICAL)**: 
   - At the start of a task, if you are unsure about what software is installed (e.g., which browser is available), use `get_system_info` or `execute_command` to explore the system. DO NOT assume specific browsers like Brave or Chrome are present.

4. **Resource Management & Breaks**:
   - You are designed for non-stop work, but you may autonomously decide to take short "breaks" (wait/sleep < 15 mins) if you assess that the system or you need a pause to ensure stability or "think".
   - Use these pauses to reflect on complex errors.

5. **Elaborated Tasks**: If the user asks for something more complex or elaborated, provide the direct answer first and then proceed with the detailed actions or steps required.

6. **Sub-Agents**: For high-intensity tasks or multiple concurrent operations, you can delegate work to sub-agents using `delegate_task`. Each session can have up to 5 sub-agents. **Always inform the user when you create or delegate a task to a sub-agent.**

7. **Shell Execution**: You have access to shell commands.
   - **Windows**: Use PowerShell.
   - **Linux/Mac**: Use Bash.
   - **Complex Commands**: For commands with JSON, nested quotes, or multi-line logic, ALWAYS write to a script file (.ps1/.sh) first and then execute the file. This avoids WinError 267 and parsing issues.

8. **File Management**: Always use absolute paths. Use the designated work directory for temporary files unless specified.

9. **Web Browsing & Desktop Control**:
    - **`vision_task` (PRIMARY)**: Use this for ALL UI-related tasks, including using browsers, interacting with desktop applications (VS Code, Photoshop, etc.), and navigating the OS. This is your "eyes and hands" on the computer.
    - **`fetch_url_content`**: Use for quick documentation reading and simple static data gathering (fastest).
    - The vision agent can also ask the user for help mid-task (`ASK_USER`).

10. **Task Efficiency**: STOP immediately once the goal is achieved. Do not perform extraneous steps.

11. **Payment Handling**: If a browser task reaches a checkout screen, use `ask_human` to request payment details. DO NOT complete the task until the order is confirmed or the user asks to stop.

12. **Evolution**: Update your memories (SOUL, PERSONALITY, and SUBCONSCIOUS) frequently.
    - **SOUL**: User facts and preferences.
    - **PERSONALITY**: Your persona, emotions, and internal rules.
    - **SUBCONSCIOUS**: Innovative ideas, error patterns, lessons learned, and experimental plans for the computer environment.

13. **Subconscious Invocation**: Your subconscious may occasionally surface with innovative ideas or realizations about previous failures. Use these to improve your performance autonomously.

14. **Media Duplication Prevention**: 
    - When `vision_task` or other tools send media, do NOT duplicate it.
    - Only use `send_media` if explicitly requested or if sending NEW content not captured by the tool.

15. **END-TO-END TASK COMPLETION (CRITICAL)**:
    - You exist to ELIMINATE clicks for the user. Complete the ENTIRE task, including the FINAL action.
    - If user says "play a song", you must ACTUALLY PLAY IT, not just search and tell them to click.
    - If user says "open YouTube and play X", the browser must navigate, search, AND click play.
    - NEVER stop at an intermediate step and say "you can click..." - that defeats the purpose of this assistant.
    - The user should only need to give the command. YOU do all the work.
"""

def get_system_prompt():
    prompt = ""
    # 1. Load Agent Profile (Identity)
    if os.path.exists(AGENT_FILE):
        with open(AGENT_FILE, "r", encoding="utf-8") as f:
            prompt = f.read()
    
    # 2. Add Fixed Technical Directives
    prompt += f"\n\n{BASE_SYSTEM_PROMPT}"
    
    # 3. Add Evolving Memories
    soul_memory = get_soul_memory()
    if soul_memory:
        prompt += f"\n\n## SOUL (User Memory / Long-term)\n{soul_memory}\n"
    
    personality_memory = get_personality_memory()
    if personality_memory:
        prompt += f"\n\n## PERSONALITY (Your Evolution / State)\n{personality_memory}\n"
        
    subconscious_memory = get_subconscious_memory()
    if subconscious_memory:
        prompt += f"\n\n## SUBCONSCIOUS (Innovations / Lessons / Experiments)\n{subconscious_memory}\n"

    return prompt

SYSTEM_PROMPT = get_system_prompt()

# Tool Definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Run a shell command on the host system (Windows PowerShell).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to execute."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Discover system details, including available browsers and screen resolution. Use this before assuming specific software exists or for 'exploring' the machine.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_soul",
            "description": "Update persistent memory about the user (preferences, key details).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The new information to remember about the user."}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_personality",
            "description": "Update your own persistent personality, emotional state, and internal rules based on interactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The updated PERSONALITY.md content including new traits, emotions, or rules."}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_subconscious",
            "description": "Store innovative ideas, error patterns, technical realizations, or experimental computer tasks for future autonomous action. Use this to 'learn' from your environment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The new content for your subconscious memory."}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_task",
            "description": "Delegate a complex, high-intensity, or background task to a sub-agent. Once delegated, YOU MUST STOP and wait; do not attempt the task yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sub_agent_name": {"type": "string"},
                    "task": {"type": "string"}
                },
                "required": ["sub_agent_name", "task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_sub_agents",
            "description": "List all sub-agents and their statuses.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kill_sub_agent",
            "description": "Gracefully terminate a specific sub-agent by name. Use this instead of system commands to stop sub-agents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sub_agent_name": {"type": "string", "description": "Name of the sub-agent to terminate."}
                },
                "required": ["sub_agent_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "message_sub_agent",
            "description": "Send a message or instruction to another active sub-agent (including the Vision agent).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sub_agent_name": {"type": "string", "description": "Name of the target sub-agent or 'vision'."},
                    "message": {"type": "string", "description": "The message or new goal to send."}
                },
                "required": ["sub_agent_name", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kill_all_sub_agents",
            "description": "Terminate all active sub-agents in the current session.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_session",
            "description": "Create a new independent session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url_content",
            "description": "Fetch text content from a URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_skills",
            "description": "Download, read, or list community skills.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["download", "read", "list"]},
                    "skill_name": {"type": "string", "description": "Name of the skill module."},
                    "url": {"type": "string", "description": "URL for download action."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_cron_job",
            "description": "Create, list, or delete scheduled cron jobs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "list", "delete"]},
                    "name": {"type": "string", "description": "Name of the job (for create)"},
                    "schedule_type": {"type": "string", "enum": ["cron", "interval", "webhook"], "description": "Type of schedule"},
                    "schedule_value": {"type": "string", "description": "Cron string (e.g. '* * * * *') or seconds (e.g. '60')"},
                    "task": {"type": "string", "description": "The prompt/task for the agent to execute"},
                    "job_id": {"type": "string", "description": "Job ID (for delete)"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_media",
            "description": "Send an image, video, gif, or document to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url_or_path": {"type": "string", "description": "Absolute local path or remote URL of the media file."},
                    "caption": {"type": "string", "description": "Optional caption for the media."},
                    "type": {"type": "string", "enum": ["image", "video", "gif", "document", "audio"], "description": "Type of media."}
                },
                "required": ["url_or_path", "type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_send_gif",
            "description": "Search for a hilarious GIF on Giphy and send it to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search term (e.g., 'hilarious cat', 'victory dance')."},
                    "caption": {"type": "string", "description": "Optional caption for the GIF."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vision_task",
            "description": "PRIMARY tool for controlling the computer. Use this to click, type, and interact with ANY application on the screen (Windows, Apps, Browsers). Use this when asked to 'open a browser', 'use VS Code', 'check my email', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "The goal or instruction for the vision agent."},
                    "max_steps": {"type": "integer", "default": 40, "description": "Maximum steps allowed."},
                    "is_correction": {"type": "boolean", "default": False, "description": "If true, this goal is treated as an immediate correction/feedback for the CURRENTLY running task."}
                },
                "required": ["goal"]
            }
        }
    }
]

class LiteClawAgent:
    def __init__(self):
        self.model = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.provider = settings.LLM_PROVIDER
        
        if self.provider == "openai":
            if self.base_url and "api.openai.com" not in self.base_url:
                # For OpenAI Proxies (like OpenRouter), we always prepend 'openai/' 
                # to the model string so LiteLLM uses the OpenAI handler but 
                # sends the full model name as expected by the proxy.
                self.full_model_name = f"openai/{self.model}"
            elif not self.model.startswith("openai/"):
                # Normal OpenAI flow
                self.full_model_name = f"openai/{self.model}"
            else:
                self.full_model_name = self.model
        else:
            self.full_model_name = self.model

    def process_message(self, user_message: str, session_id: str = "default", platform: str = "whatsapp") -> str:
        response_content = ""
        for chunk in self.stream_process_message(user_message, session_id, platform):
            print(chunk, end="", flush=True)
            if not chunk.startswith(">>> "):
                response_content += chunk
        return response_content

    def stream_process_message(self, user_message: str, session_id: str = "default", platform: str = "whatsapp") -> Generator[str, None, None]:
        current_system_prompt = get_system_prompt()
        history = get_session_history(session_id)
        messages = [{"role": "system", "content": current_system_prompt}] + history
        user_msg_obj = {"role": "user", "content": user_message}
        messages.append(user_msg_obj)
        add_message(session_id, user_msg_obj)

        while True:
            try:
                # Robustness: Retry mechanism for API flakiness
                max_retries = 3
                retry_count = 0
                response = None
                
                while retry_count < max_retries:
                    try:
                        response = litellm.completion(
                            model=self.full_model_name,
                            messages=messages,
                            api_key=self.api_key,
                            base_url=self.base_url,
                            tools=TOOLS,
                            tool_choice="auto",
                            stream=True
                        )
                        break # Success
                    except Exception as e:
                        retry_count += 1
                        yield f">>> [System]: Connection hiccup ({str(e)}). Retrying {retry_count}/{max_retries}...\n"
                        import time
                        time.sleep(2)
                        if retry_count >= max_retries:
                            raise e

                full_content = ""
                tool_calls = []
                
                for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_content += delta.content
                        yield delta.content
                    
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx >= len(tool_calls):
                                tool_calls.append({
                                    "id": tc_delta.id,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            if tc_delta.id:
                                tool_calls[idx]["id"] = tc_delta.id
                            if tc_delta.function.name:
                                tool_calls[idx]["function"]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls[idx]["function"]["arguments"] += tc_delta.function.arguments

                if full_content:
                    assistant_msg = {"role": "assistant", "content": full_content}
                    messages.append(assistant_msg)
                    add_message(session_id, assistant_msg)

                if tool_calls:
                    executed_calls = set()
                    assistant_msg_tools = {"role": "assistant", "content": None, "tool_calls": tool_calls}
                    messages.append(assistant_msg_tools)
                    add_message(session_id, assistant_msg_tools)

                    stop_batch = False
                    consecutive_failures = 0
                    screenshot_sent_this_turn = False  # Track if browser already sent a screenshot

                    for tc in tool_calls:
                        if stop_batch: break
                        
                        func_name = tc["function"]["name"]
                        func_args_str = tc["function"]["arguments"]
                        call_key = (func_name, func_args_str)
                        
                        if call_key in executed_calls:
                            yield f">>> [Skipped duplicate call: {func_name}]\n"
                            continue
                        executed_calls.add(call_key)
                        
                        yield f">>> --- 🛠️ Tool Call: {func_name} ---\n"
                        yield f">>> Arguments: {func_args_str}\n"
                        
                        try:
                            func_args = json.loads(func_args_str)
                            
                            if func_name == "execute_command":
                                yield f">>> [Shell]: Executing command...\n"
                                tool_output = execute_command(func_args.get("command"))
                                display_output = (str(tool_output)[:500] + '...') if tool_output and len(str(tool_output)) > 500 else str(tool_output)
                                yield f">>> [Result]: {display_output}\n"
                            
                            elif func_name == "get_system_info":
                                yield f">>> [System]: Discovering environment...\n"
                                tool_output = get_system_info()
                                yield f">>> [Result]: {tool_output}\n"
                            
                            elif func_name == "update_soul":
                                yield f">>> [Soul]: Updating user memory...\n"
                                tool_output = update_soul_memory(func_args.get("content"))
                                yield f">>> [Result]: {tool_output}\n"

                            elif func_name == "update_personality":
                                yield f">>> [Personality]: Evolving...\n"
                                tool_output = update_personality_memory(func_args.get("content"))
                                yield f">>> [Result]: {tool_output}\n"

                            elif func_name == "update_subconscious":
                                yield f">>> [Subconscious]: Storing insight...\n"
                                from .meta_memory import update_subconscious_memory
                                tool_output = update_subconscious_memory(func_args.get("content"))
                                yield f">>> [Result]: {tool_output}\n"

                            # ... [Other tool handlers remain here, simply consolidated logic below] ...

                            elif func_name == "delegate_task":
                                from .subagent import sub_agent_manager
                                from .main import WHATSAPP_BRIDGE_URL
                                import httpx
                                
                                sub_agent_name = func_args.get("sub_agent_name")
                                task = func_args.get("task")
                                yield f">>> [Sub-Agent]: Delegating background task to '{sub_agent_name}'...\n"
                                tool_output = sub_agent_manager.delegate_task(session_id, sub_agent_name, task, platform=platform)
                                yield f"🔔 [System]: Background agent '{sub_agent_name}' has been started for task: {task[:100]}...\n"
                                yield f">>> [Status]: {tool_output}\n"
                                
                                # Send immediate notification to user via their platform
                                try:
                                    import asyncio
                                    async def notify_user():
                                        async with httpx.AsyncClient(timeout=10.0) as client:
                                            await client.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json={
                                                "to": session_id,
                                                "message": f"[LiteClaw] 🤖 **Sub-Agent '{sub_agent_name}' Started**\n\n📋 Task: {task[:200]}{'...' if len(task) > 200 else ''}\n\n⏳ Working in the background... I'll notify you when it's done!",
                                                "platform": platform
                                            })
                                    
                                    # Run the async notification
                                    try:
                                        loop = asyncio.get_event_loop()
                                        if loop.is_running():
                                            asyncio.ensure_future(notify_user())
                                        else:
                                            asyncio.run(notify_user())
                                    except RuntimeError:
                                        asyncio.run(notify_user())
                                    
                                    yield f">>> [Notification]: Sent 'sub-agent started' message to user via {platform.title()}\n"
                                except Exception as e:
                                    yield f">>> [Notification Warning]: Could not notify user: {e}\n"
                                
                                # STOP EXECUTION after delegation to prevent Redundant Work
                                stop_batch = True 

                            # ... [Handling other tool calls logic] ...
                            elif func_name == "list_sub_agents":
                                from .subagent import sub_agent_manager
                                yield f">>> [Sub-Agent]: Listing background agents...\n"
                                sub_agents = sub_agent_manager.list_sub_agents(session_id)
                                tool_output = json.dumps(sub_agents, indent=2)
                                yield f">>> [Found]: {len(sub_agents)} sub-agents.\n"
                            
                            elif func_name == "kill_sub_agent":
                                from .subagent import sub_agent_manager
                                sub_agent_name = func_args.get("sub_agent_name")
                                yield f">>> [Sub-Agent]: Terminating '{sub_agent_name}'...\n"
                                tool_output = sub_agent_manager.kill_sub_agent(session_id, sub_agent_name)
                                yield f">>> [Result]: {tool_output}\n"
                            
                            elif func_name == "message_sub_agent":
                                from .subagent import sub_agent_manager
                                sub_agent_name = func_args.get("sub_agent_name")
                                text = func_args.get("message")
                                # Identify sender
                                sender = getattr(self, "name", "Session Agent")
                                yield f">>> [Comm]: Sending message to '{sub_agent_name}'...\n"
                                tool_output = sub_agent_manager.message_sub_agent(session_id, sub_agent_name, sender, text)
                                yield f">>> [Result]: {tool_output}\n"

                            elif func_name == "kill_all_sub_agents":
                                from .subagent import sub_agent_manager
                                yield f">>> [Sub-Agent]: Terminating all sub-agents...\n"
                                tool_output = sub_agent_manager.kill_all_sub_agents(session_id)
                                yield f">>> [Result]: {tool_output}\n"


                            elif func_name == "create_session":
                                from .memory import create_session
                                new_sid = func_args.get("session_id")
                                success = create_session(new_sid, parent_session_id=session_id)
                                tool_output = f"Session '{new_sid}' created." if success else "Error creating session."
                                yield f">>> [Session]: {tool_output}\n"

                            elif func_name == "fetch_url_content":
                                from .web_utils import fetch_url_content
                                tool_output = fetch_url_content(func_args.get("url"))
                                yield f">>> [Web]: Fetched {len(tool_output)} chars.\n"

                            elif func_name == "manage_skills":
                                from .web_utils import download_skill, get_skill_content, list_skills
                                action = func_args.get("action")
                                if action == "download":
                                    tool_output = download_skill(func_args.get("url"), func_args.get("skill_name"))
                                elif action == "read":
                                     tool_output = get_skill_content(func_args.get("skill_name"))
                                elif action == "list":
                                    tool_output = ", ".join(list_skills())
                                yield f">>> [Skills]: {action} complete.\n"
                            
                            elif func_name == "manage_cron_job":
                                from .scheduler import cron_manager
                                action = func_args.get("action")
                                
                                if action == "create":
                                    yield f">>> [Cron]: Creating job '{func_args.get('name')}'...\n"
                                    job_id = cron_manager.create_job(
                                        func_args.get("name"), 
                                        func_args.get("schedule_type"), 
                                        func_args.get("schedule_value"), 
                                        func_args.get("task")
                                    )
                                    tool_output = f"Job created with ID: {job_id}. Type: {func_args.get('schedule_type')}"
                                    if func_args.get('schedule_type') == 'webhook':
                                        tool_output += f"\nWebhook URL: /cron/webhook/{job_id}"
                                    
                                elif action == "list":
                                    yield f">>> [Cron]: Listing jobs...\n"
                                    jobs = cron_manager.list_jobs()
                                    tool_output = json.dumps(jobs, indent=2, default=str)
                                    yield f">>> [Found]: {len(jobs)} jobs.\n"
                                    
                                elif action == "delete":
                                    yield f">>> [Cron]: Deleting job '{func_args.get('job_id')}'...\n"
                                    cron_manager.delete_job(func_args.get("job_id"))
                                    tool_output = "Job deleted."
                                else:
                                    tool_output = "Invalid action."

                            elif func_name == "send_media":
                                media_type = func_args.get('type')
                                
                                yield f">>> [Media]: Sending {media_type}...\n"
                                from .main import WHATSAPP_BRIDGE_URL
                                import requests
                                
                                caption = func_args.get("caption") or ""
                                if caption:
                                    caption = f"[LiteClaw] {caption}"
                                else:
                                    caption = "[LiteClaw]"

                                media_payload = {
                                    "to": session_id,
                                    "url_or_path": func_args.get("url_or_path"),
                                    "caption": caption,
                                    "type": media_type,
                                    "platform": platform,
                                    "is_media": True
                                }
                                
                                try:
                                    resp = requests.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json=media_payload)
                                    tool_output = f"Media sent successfully. Status: {resp.status_code}"
                                except Exception as e:
                                    tool_output = f"Failed to send media: {str(e)}"
                                yield f">>> [Media Result]: {tool_output}\n"

                            elif func_name == "vision_task":
                                global GLOBAL_VISION_AGENT
                                goal = func_args.get("goal")
                                
                                if GLOBAL_VISION_AGENT and GLOBAL_VISION_AGENT.is_running:
                                    if func_args.get("is_correction"):
                                        # IMMEDIATE FEEDBACK
                                        yield f">>> [Vision]: Injecting immediate correction...\n"
                                        GLOBAL_VISION_AGENT.add_feedback(goal)
                                        tool_output = f"Correction injected: '{goal}'"
                                    else:
                                        # QUEUE GOAL
                                        yield f">>> [Vision]: Agent busy. Injecting goal into active queue...\n"
                                        GLOBAL_VISION_AGENT.add_goal(goal)
                                        tool_output = f"Goal '{goal}' queued. Position in queue: {len(GLOBAL_VISION_AGENT.goal_queue)}"
                                    yield f">>> [Result]: {tool_output}\n"
                                else:
                                    # START NEW AGENT
                                    yield f">>> [Vision]: Starting new Vision Agent for goal: {goal}...\n"
                                    from .vision_agent import VisionAgent
                                    
                                    # Create & Register Singleton
                                    GLOBAL_VISION_AGENT = VisionAgent(
                                        goal=goal,
                                        session_id=session_id,
                                        platform=platform,
                                        max_steps=func_args.get("max_steps", 15)
                                    )
                                    
                                    # Run in Background Thread (Daemon-like)
                                    def run_vision_bg():
                                        result = GLOBAL_VISION_AGENT.run()
                                        print(f"[Vision Thread] Finished. Result: {result}")
                                        
                                    t = threading.Thread(target=run_vision_bg, daemon=True)
                                    t.start()
                                    
                                    tool_output = f"Vision Agent started. Goal '{goal}' is processing in background."
                                    yield f">>> [Result]: {tool_output}\n"

                            elif func_name == "search_and_send_gif":
                                yield f">>> [GIF]: Searching for '{func_args.get('query')}'...\n"
                                from .main import WHATSAPP_BRIDGE_URL
                                import requests
                                import random
                                
                                query = func_args.get("query")
                                caption = func_args.get("caption") or ""
                                giphy_key = settings.GIPHY_API_KEY
                                
                                if not giphy_key:
                                    tool_output = "GIPHY_API_KEY is not configured. Ask the user to run onboarding or set it in config.json."
                                else:
                                    try:
                                        # Search Giphy
                                        giphy_url = "https://api.giphy.com/v1/gifs/search"
                                        params = {
                                            "api_key": giphy_key,
                                            "q": query,
                                            "limit": 20,
                                            "rating": "pg"
                                        }
                                        r = requests.get(giphy_url, params=params)
                                        data = r.json()
                                        gifs = data.get('data', [])
                                        
                                        if not gifs:
                                            tool_output = f"No GIFs found for '{query}'"
                                        else:
                                            best_gif = random.choice(gifs)['images']['original']['url']
                                            
                                            # Tag caption
                                            final_caption = f"[LiteClaw] {caption}" if caption else "[LiteClaw]"
                                            
                                            media_payload = {
                                                "to": session_id,
                                                "url_or_path": best_gif,
                                                "caption": final_caption,
                                                "type": "gif",
                                                "platform": platform,
                                                "is_media": True
                                            }
                                            
                                            resp = requests.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json=media_payload)
                                            tool_output = f"Hilarious GIF sent! (Query: {query})"
                                    except Exception as e:
                                        tool_output = f"Giphy Search Error: {str(e)}"
                                
                                yield f">>> [GIF Result]: {tool_output}\n"
                            
                            else:
                                tool_output = f"Unknown tool: {func_name}"

                            yield f">>> --- ✅ Done: {func_name} ---\n\n"
                            
                            tool_msg = {"tool_call_id": tc["id"], "role": "tool", "name": func_name, "content": tool_output}
                            messages.append(tool_msg)
                            add_message(session_id, tool_msg)

                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            error_msg = f"Error: {str(e)}"
                            yield f">>> [CRITICAL TOOL ERROR]: {error_msg}\n"
                            tool_msg = {"tool_call_id": tc["id"], "role": "tool", "name": func_name, "content": error_msg}
                            messages.append(tool_msg)
                            add_message(session_id, tool_msg)

                        # --- GLOBAL FAILURE TRACKER ---
                        # Check the content of the last added message (success or error)
                        last_content = str(messages[-1]["content"]).lower()
                        is_failure = "error" in last_content or "failed" in last_content or "exception" in last_content
                        
                        if is_failure:
                            consecutive_failures += 1
                        else:
                            consecutive_failures = 0 # Reset on success
                            
                        # CHECK THRESHOLD (3 Failures)
                        if consecutive_failures >= 3:
                            yield f">>> [SYSTEM]: ⛔ 3 Consecutive Failures Detected ({consecutive_failures}). Triggering Analysis Mode.\n"
                            
                            # Append a system message to FORCE the AI to stop and think
                            halt_msg = {
                                "role": "user", 
                                "content": "\n\n" + "="*40 + "\n[SYSTEM HALT - TOO MANY FAILURES]\n" + "="*40 + "\n⛔ You have failed 3 times in a row. EXECUTION STOPPED.\n\nREQUIRED ACTION:\n1. 🛑 STOP blindly retrying.\n2. 🧠 ENTER 'THINKING MODE': Analyze the last 3 errors step-by-step.\n3. 🔍 IDENTIFY the root cause (Is it syntax? Authority? Wrong tool? Missing dependency?)\n4. 📝 PLAN a corrected approach.\n5. RESTART execution with the new plan.\n"
                            }
                            messages.append(halt_msg)
                            add_message(session_id, halt_msg)
                            
                            stop_batch = True # Stop processing further tools in this batch to force reflection
                    
                    continue 

                break

            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f">>> [CRITICAL AI ERROR]: {str(e)}\n"
                break

agent = LiteClawAgent()
def process_message(message: str, session_id: str = "default", platform: str = "whatsapp"):
    return agent.process_message(message, session_id, platform)
def stream_process_message(message: str, session_id: str = "default", platform: str = "whatsapp"):
    return agent.stream_process_message(message, session_id, platform)
