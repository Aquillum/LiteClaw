import json
import os
import requests
from typing import List, Dict, Any, Generator
from .config import settings
from .tools import execute_command
from .memory import add_message, get_session_history
from .meta_memory import get_soul_memory, update_soul_memory
import litellm

def get_system_prompt():
    soul_memory = get_soul_memory()
    prompt = ""
    # Load AGENT.md
    agent_md_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "AGENT.md")
    if os.path.exists(agent_md_path):
        with open(agent_md_path, "r", encoding="utf-8") as f:
            prompt = f.read()
    
    prompt += f"\n\n## SOUL (User Memory)\n{soul_memory}\n"
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
            "name": "update_soul",
            "description": "Update persistent memory about the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The new information to remember."}
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
            "name": "browser_task",
            "description": "Perform complex tasks in a real browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "show_browser": {"type": "boolean", "default": False},
                    "disable_security": {"type": "boolean", "default": True, "description": "Disable browser security watchdogs to allow file:// URLs or sensitive domains."},
                    "allowed_domains": {"type": "array", "items": {"type": "string"}, "description": "Explicitly allow these domains (e.g. ['google.com', 'file://*'])."},
                    "browser_name": {"type": "string", "description": "Specify a browser to use (e.g. 'brave', 'chrome')."}
                },
                "required": ["task"]
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
    }
]

class LiteClawAgent:
    def __init__(self):
        self.model = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.provider = settings.LLM_PROVIDER
        
        if self.provider == "openai" and not self.model.startswith("openai/"):
            self.full_model_name = f"openai/{self.model}"
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
                            
                            elif func_name == "update_soul":
                                yield f">>> [Soul]: Updating memory...\n"
                                tool_output = update_soul_memory(func_args.get("content"))
                                yield f">>> [Result]: {tool_output}\n"

                            elif func_name == "delegate_task":
                                from .subagent import sub_agent_manager
                                sub_agent_name = func_args.get("sub_agent_name")
                                task = func_args.get("task")
                                yield f">>> [Sub-Agent]: Delegating background task to '{sub_agent_name}'...\n"
                                tool_output = sub_agent_manager.delegate_task(session_id, sub_agent_name, task)
                                yield f"🔔 [System]: Background agent '{sub_agent_name}' has been started for task: {task[:100]}...\n"
                                yield f">>> [Status]: {tool_output}\n"
                                # STOP EXECUTION after delegation to prevent Redundant Work
                                stop_batch = True 

                            elif func_name == "list_sub_agents":
                                from .subagent import sub_agent_manager
                                yield f">>> [Sub-Agent]: Listing background agents...\n"
                                sub_agents = sub_agent_manager.list_sub_agents(session_id)
                                tool_output = json.dumps(sub_agents, indent=2)
                                yield f">>> [Found]: {len(sub_agents)} sub-agents.\n"

                            elif func_name == "browser_task":
                                from .browser_utils import run_browser_task
                                task_desc = func_args.get("task")
                                show_browser = func_args.get("show_browser", False)
                                disable_security = func_args.get("disable_security", True)
                                allowed_domains = func_args.get("allowed_domains")
                                browser_name = func_args.get("browser_name")
                                
                                yield f">>> [Browser]: Launching (Show={show_browser}, SecDisable={disable_security}, Browser={browser_name}). Task: {task_desc}\n"
                                tool_output = run_browser_task(
                                    task_desc, 
                                    show_browser=show_browser, 
                                    disable_security=disable_security, 
                                    allowed_domains=allowed_domains,
                                    executable_path=browser_name
                                )
                                display_result = (str(tool_output)[:500] + "...") if tool_output else "No result returned."
                                yield f">>> [Browser Result]: {display_result}\n"

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
                                yield f">>> [Media]: Sending {func_args.get('type')}...\n"
                                from .main import WHATSAPP_BRIDGE_URL
                                import requests
                                
                                # Resolve platform from session (simplified: we assume session_id is either number or chat_id)
                                # In main.py we have the platform context, but here we might need to guess or pass it.
                                # For now, we'll let the bridge handle it if we genericize it.
                                
                                caption = func_args.get("caption") or ""
                                if caption:
                                    caption = f"[LiteClaw] {caption}"
                                else:
                                    caption = "[LiteClaw]"

                                media_payload = {
                                    "to": session_id,
                                    "url_or_path": func_args.get("url_or_path"),
                                    "caption": caption,
                                    "type": func_args.get("type"),
                                    "platform": platform,
                                    "is_media": True
                                }
                                
                                try:
                                    resp = requests.post(f"{WHATSAPP_BRIDGE_URL}/whatsapp/send", json=media_payload)
                                    tool_output = f"Media sent successfully. Status: {resp.status_code}"
                                except Exception as e:
                                    tool_output = f"Failed to send media: {str(e)}"
                                yield f">>> [Media Result]: {tool_output}\n"

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
