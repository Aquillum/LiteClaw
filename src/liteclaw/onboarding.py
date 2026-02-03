import questionary
import json
import os
import subprocess
import platform
import shutil
import time
import webbrowser
from rich.console import Console
from rich.panel import Panel

console = Console()
CONFIG_FILE = "config.json"

# LiteLLM Provider Configuration
# Based on: https://docs.litellm.ai/docs/providers
PROVIDERS = {
    "OpenAI": {
        "provider": "openai",  # LiteLLM provider name
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "description": "Official OpenAI API",
        "models": [
            "gpt-4o",
            "gpt-4o-mini", 
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini"
        ],
        "model_prefix": ""  # Agent adds openai/ prefix if missing
    },
    "OpenRouter": {
        "provider": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "description": "Access 200+ models via unified API",
        "models": [
            "anthropic/claude-opus-4.5",
            "openai/gpt-5.2-pro",
            "openai/gpt-5.2",
            "google/gemini-3-flash-preview",
            "anthropic/claude-sonnet-4",
            "deepseek/deepseek-v3.2",
            "xiaomi/mimo-v2-flash-309b-moe",
            "mistral/devstral-2-2512",
            "bytedance/seed-1.6-flash",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "google/gemini-2.0-flash-exp",
            "google/gemini-pro-1.5",
            "openai/gpt-4o",
            "meta-llama/llama-3.3-70b-instruct",
            "mistralai/mixtral-8x22b",
            "qwen/qwen-2.5-72b-instruct",
            "deepseek/deepseek-chat"
        ],
        "model_prefix": ""  # Handled by agent's new OpenAI proxy logic
    },
    "Groq": {
        "provider": "openai",  # Use OpenAI-compatible bridge
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "description": "Ultra-fast inference with open models",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ],
        "model_prefix": "" 
    },
    "DeepSeek": {
        "provider": "openai", # Use OpenAI-compatible bridge
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "description": "High-quality Chinese AI models",
        "models": [
            "deepseek-chat",
            "deepseek-coder",
            "deepseek-reasoner"
        ],
        "model_prefix": ""
    },
    "Hugging Face": {
        "provider": "huggingface",
        "base_url": None, # Uses hub by default
        "api_key_env": "HUGGINGFACE_API_KEY",
        "description": "Access open-source models via HF Hub",
        "models": [
            "meta-llama/Llama-3.2-3B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "google/gemma-2-27b-it"
        ],
        "model_prefix": "huggingface/"
    },
    "Ollama (Local)": {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "api_key_env": None,
        "description": "Run models locally on your machine",
        "models": [
            "llama3.2",
            "llama3.1",
            "qwen2.5",
            "deepseek-r1"
        ],
        "model_prefix": "ollama/"
    }
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_default_work_dir():
    system = platform.system()
    if system == "Windows": return r"C:\liteclaw"
    return os.path.expanduser("~/liteclaw")

def ensure_work_dir(work_dir: str) -> bool:
    try:
        if not os.path.exists(work_dir):
            os.makedirs(work_dir, exist_ok=True)
        subdirs = ["screenshots", "configs", "notes", "exports", "sessions"]
        for subdir in subdirs:
            os.makedirs(os.path.join(work_dir, subdir), exist_ok=True)
        return True
    except Exception as e:
        console.print(f"[red]Error creating directory: {e}[/red]")
        return False

def setup_work_dir(current_config=None):
    console.print("\n[bold]0. Work Directory Setup[/bold]")
    default_dir = current_config.get("WORK_DIR") if current_config else get_default_work_dir()
    
    use_default = questionary.confirm(f"Use work directory? ({default_dir})", default=True).ask()
    if use_default is None: return None
    
    if use_default:
        work_dir = default_dir
    else:
        work_dir = questionary.path("Enter work directory path:", default=default_dir, only_directories=True).ask()
        if not work_dir: work_dir = default_dir
    
    if ensure_work_dir(work_dir):
        console.print(f"[green]📂 Work Directory Set: {work_dir}[/green]")
        return work_dir
    return None

def check_system_dependencies():
    console.print("\n[bold]⚙️ Checking System Dependencies...[/bold]")
    
    # 1. Check Node.js
    node_ok = False
    try:
        # Check version
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
        version_str = result.stdout.strip()
        # Parse version (e.g., v18.12.1 -> 18)
        major_version = int(version_str.lstrip('v').split('.')[0])
        
        if major_version < 18:
            console.print(f"[red]⚠ Node.js version {version_str} is TOO OLD.[/red]")
            console.print("[yellow]LiteClaw requires Node.js v18 or higher for messaging bridges.[/yellow]")
            console.print("[dim]Please upgrade Node.js: https://nodejs.org[/dim]")
        else:
            console.print(f"[green]✓ Node.js {version_str} found[/green]")
            node_ok = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[red]✗ Node.js NOT found! Please install Node.js (v18+) for messaging bridges.[/red]")
    except Exception as e:
        console.print(f"[yellow]⚠ Error checking Node.js: {e}[/yellow]")
    
    # 1.1 Check Homebrew (macOS Only)
    if platform.system() == "Darwin":
        try:
            subprocess.run(["brew", "--version"], capture_output=True, text=True, check=True)
            console.print("[green]✓ Homebrew found[/green]")
        except:
            console.print("[yellow]⚠ Homebrew NOT found. Recommended for macOS: https://brew.sh[/yellow]")
    
    # 2. Check Python Vision Libraries
    vision_ok = True
    system = platform.system()
    is_mac = system == "Darwin"
    is_silicon = is_mac and platform.machine() == "arm64"
    
    if is_mac:
        console.print(f"[cyan] Detected macOS{' (Apple Silicon)' if is_silicon else ''}[/cyan]")
        
    try:
        import PIL
        import pyautogui
        
        # Verify display access/Permissions
        try:
             width, height = pyautogui.size()
             console.print(f"[green]✓ Vision dependencies found (Display: {width}x{height})[/green]")
             if is_mac and width < 100: # Heuristic for denied permissions
                 console.print("[red]⚠ macOS Permission Error: Display size reported as too small.[/red]")
                 raise Exception("Display permissions likely denied")
        except Exception as e:
             console.print(f"[yellow]⚠ Vision Display Error: {e}[/yellow]")
             if is_mac:
                 console.print("\n[bold red]CRITICAL: macOS Permissions Required[/bold red]")
                 console.print("LiteClaw needs [bold]Screen Recording[/bold] and [bold]Accessibility[/bold] permissions.")
                 console.print("1. Open [bold]System Settings > Privacy & Security[/bold]")
                 console.print("2. Grant permissions to your [bold]Terminal/IDE[/bold] and [bold]Python[/bold].")
                 console.print("3. Restart your Terminal after granting.")
             else:
                 console.print("[dim]Note: This is normal on headless servers or VMs without X11 setup.[/dim]")
             vision_ok = False
    except ImportError as e:
        missing = str(e).split("'")[-2]
        console.print(f"[yellow]⚠ Missing dependency: {missing}[/yellow]")
        if is_mac:
            console.print("[yellow]For macOS Vision support, run:[/yellow]")
            console.print("[bold]pip install pyautogui Pillow pyobjc-core pyobjc-framework-Quartz[/bold]")
        else:
            console.print("[yellow]Run: pip install pyautogui Pillow[/yellow]")
        vision_ok = False
    except Exception as e:
        console.print(f"[yellow]⚠ Vision init error: {e}[/yellow]")
        vision_ok = False
        
    return node_ok, vision_ok

def setup_llm(current_config=None):
    console.print("\n[bold]1. LLM Provider Setup[/bold]")
    console.print("[dim]💡 Tip: OpenRouter gives access to 200+ models with a single API key[/dim]\n")
    
    # Build provider selection choices with descriptions
    provider_choices = [
        f"{name} - {config['description']}" 
        for name, config in PROVIDERS.items()
    ]
    
    # Determine default
    default_choice = provider_choices[1]  # Default to OpenRouter
    if current_config and current_config.get("LLM_BASE_URL"):
        for name, config in PROVIDERS.items():
            if config["base_url"] in current_config.get("LLM_BASE_URL", ""):
                default_choice = f"{name} - {config['description']}"
                break
    
    selected = questionary.select(
        "Select LLM Provider:",
        choices=provider_choices,
        default=default_choice
    ).ask()
    if not selected: return None
    
    # Extract provider name from selection (e.g., "Groq - Ultra-fast inference" -> "Groq")
    provider_name = selected.split(" - ")[0].strip()
    provider_config = PROVIDERS[provider_name]
    
    console.print(f"[dim]Debug: Selected provider '{provider_name}'[/dim]")
    
    # Get API key (if needed)
    api_key = ""
    if provider_config["api_key_env"]:
        existing_key = current_config.get("LLM_API_KEY", "") if current_config else ""
        api_key = questionary.password(
            f"Enter API Key for {provider_name}:",
            default=existing_key
        ).ask()
        if api_key is None: return None
        api_key = api_key.strip()
    else:
        console.print("[yellow]ℹ️ Local Ollama doesn't require an API key[/yellow]")
        api_key = "not-needed"
    
    # Handle custom base URL for Ollama
    base_url = provider_config["base_url"]
    if provider_name == "Ollama (Local)":
        custom_url = questionary.confirm(
            "Using default Ollama URL (http://localhost:11434)?",
            default=True
        ).ask()
        if not custom_url:
            base_url = questionary.text(
                "Enter Ollama URL:",
                default=base_url
            ).ask()
            if not base_url: base_url = provider_config["base_url"]
    
    # Model selection with better UX
    model_choices = provider_config["models"] + ["Enter custom model name"]
    default_model = current_config.get("LLM_MODEL", "").replace(provider_config["model_prefix"], "") if current_config else None
    
    console.print(f"\n[bold]Select Model for {provider_name}:[/bold]")
    console.print(f"[dim]Available {len(provider_config['models'])} models[/dim]")
    
    model = questionary.select(
        "Choose a model:",
        choices=model_choices,
        default=default_model if default_model in model_choices else None
    ).ask()
    if model is None: return None
    
    if model == "Enter custom model name":
        console.print(f"\n[yellow]💡 For {provider_name}, use format: {provider_config['model_prefix']}model-name[/yellow]")
        if provider_name == "OpenRouter":
            console.print("[dim]Examples: openrouter/anthropic/claude-3.5-sonnet, openrouter/google/gemini-pro[/dim]")
        
        model = questionary.text(
            "Enter full model name:",
            default=default_model or f"{provider_config['model_prefix']}"
        ).ask()
        if model is None: return None
    else:
        # Add prefix if not already present
        if not model.startswith(provider_config["model_prefix"]):
            model = f"{provider_config['model_prefix']}{model}"
    
    console.print(f"\n[green]✅ LLM Configuration:[/green]")
    console.print(f"  Provider: {provider_name}")
    console.print(f"  Model: {model}")
    console.print(f"  Base URL: {base_url}")
    
    return {
        "LLM_PROVIDER": provider_config["provider"],  # Use LiteLLM provider name
        "LLM_BASE_URL": base_url,
        "LLM_API_KEY": api_key,
        "LLM_MODEL": model
    }

def setup_vision_llm(current_config, main_llm_config):
    """
    Setup a separate Vision LLM if the main model is not vision-capable.
    """
    # Simple heuristic to check if main model is vision-capable
    main_model = main_llm_config.get("LLM_MODEL", "").lower()
    vision_keywords = ["gpt-4o", "gemini", "claude-3", "vision", "vl", "pixtral", "llava"]
    is_vision_capable = any(k in main_model for k in vision_keywords)
    
    console.print("\n[bold]1.1. Vision Model Setup[/bold]")
    if is_vision_capable:
        console.print(f"[green]✅ Main model '{main_model}' appears to have Vision capabilities.[/green]")
        use_separate = questionary.confirm(
            "Do you want to configure a separate Vision Model anyway? (Not needed usually)", 
            default=False
        ).ask()
        if not use_separate:
            return {}
    else:
        console.print(f"[yellow]⚠️ Main model '{main_model}' is likely text-only.[/yellow]")
        console.print("[dim]For desktop automation, a Vision Model is REQUIRED.[/dim]")
        use_separate = questionary.confirm(
            "Configure a separate Vision Model? (Recommended)", 
            default=True
        ).ask()
        if not use_separate:
            return {}

    console.print("\n[bold]Select Vision LLM Provider:[/bold]")
    
    # Reuse providers logic but filter/sort for vision
    provider_choices = []
    for name, config in PROVIDERS.items():
        # Tag known vision providers
        if name in ["OpenRouter", "OpenAI", "Google", "Anthropic"]:
             provider_choices.append(f"{name} - {config['description']}")
        else:
             provider_choices.append(f"{name} - {config['description']}")

    # Determine default
    default_choice = provider_choices[1]  # OpenRouter
    
    selected = questionary.select(
        "Select Vision Provider:",
        choices=provider_choices,
        default=default_choice
    ).ask()
    if not selected: return {}
    
    provider_name = selected.split(" - ")[0].strip()
    provider_config = PROVIDERS[provider_name]
    
    # API Key
    api_key = ""
    # Check if we can reuse main API key if provider matches
    if main_llm_config.get("LLM_PROVIDER") == provider_config["provider"] and main_llm_config.get("LLM_API_KEY"):
         reuse_key = questionary.confirm(f"Reuse API Key from main configuration?", default=True).ask()
         if reuse_key:
             api_key = main_llm_config.get("LLM_API_KEY")

    if not api_key and provider_config["api_key_env"]:
        existing_key = current_config.get("VISION_LLM_API_KEY", "") if current_config else ""
        api_key = questionary.password(
            f"Enter Vision API Key for {provider_name}:",
            default=existing_key
        ).ask()
        if api_key: api_key = api_key.strip()
    
    # Base URL
    base_url = provider_config["base_url"]
    if main_llm_config.get("LLM_PROVIDER") == provider_config["provider"]:
        base_url = main_llm_config.get("LLM_BASE_URL", base_url)

    # Model Selection
    model_choices = provider_config["models"] + ["Enter custom model name"]
    
    console.print(f"\n[bold]Select Vision Model:[/bold]")
    model = questionary.select(
        "Choose a model:",
        choices=model_choices
    ).ask()
    
    if model == "Enter custom model name":
        model = questionary.text("Enter full model name:").ask()
    else:
        if not model.startswith(provider_config["model_prefix"]):
            model = f"{provider_config['model_prefix']}{model}"

    return {
        "VISION_LLM_PROVIDER": provider_config["provider"],
        "VISION_LLM_BASE_URL": base_url,
        "VISION_LLM_API_KEY": api_key,
        "VISION_LLM_MODEL": model
    }


def setup_bridges(current_config=None):
    console.print("\n[bold]2. Messaging Bridges[/bold]")
    config = {}
    
    choices = [
        questionary.Choice("WhatsApp (requires phone scan)", checked=bool(current_config.get("WHATSAPP_TYPE") if current_config else False)),
        questionary.Choice("Telegram (requires Bot Token)", checked=bool(current_config.get("TELEGRAM_BOT_TOKEN") if current_config else False)),
        questionary.Choice("Slack (requires Bot Token)", checked=bool(current_config.get("SLACK_BOT_TOKEN") if current_config else False))
    ]
    
    bridges = questionary.checkbox("Select channels to enable:", choices=choices).ask()
    if bridges is None: return None

    if "WhatsApp (requires phone scan)" in bridges:
        config["WHATSAPP_TYPE"] = "node_bridge"
        console.print("\n[yellow]💡 WhatsApp Setup Guide:[/yellow]")
        console.print("1. We use a real browser instance (Puppeteer) to connect to WhatsApp Web.")
        console.print("2. You will scan a QR code once, and session will be saved locally.")
        console.print("3. Supports Multi-Device login (phone doesn't need to be online).\n")
        
        limit = questionary.confirm("Limit allowed phone numbers?", default=bool(current_config.get("WHATSAPP_ALLOWED_NUMBERS") if current_config else True)).ask()
        if limit:
            existing = ",".join(current_config.get("WHATSAPP_ALLOWED_NUMBERS", [])) if current_config else ""
            console.print("[dim]Enter numbers with country code, no + or spaces (e.g. 919876543210)[/dim]")
            nums = questionary.text("Allowed Numbers (comma-sep):", default=existing).ask()
            if nums: config["WHATSAPP_ALLOWED_NUMBERS"] = [n.strip() for n in nums.split(",") if n.strip()]

    if "Telegram (requires Bot Token)" in bridges:
        console.print("\n[yellow]💡 Telegram Setup Guide:[/yellow]")
        console.print("1. Message @BotFather on Telegram.")
        console.print("2. Send command /newbot and follow instructions.")
        console.print("3. Copy the HTTP API Token provided.\n")
        
        token = questionary.text("Enter TG Token:", default=current_config.get("TELEGRAM_BOT_TOKEN", "") if current_config else "").ask()
        if token: config["TELEGRAM_BOT_TOKEN"] = token.strip()
        
        limit_tg = questionary.confirm("Limit allowed Telegram users?", default=bool(current_config.get("TELEGRAM_ALLOWED_IDS") if current_config else True)).ask()
        if limit_tg:
            existing_tg = ",".join(current_config.get("TELEGRAM_ALLOWED_IDS", [])) if current_config else ""
            console.print("[dim]Enter User IDs or bot:chatid format (comma-sep). Leaving empty allows all.[/dim]")
            tg_ids = questionary.text("Allowed IDs:", default=existing_tg).ask()
            if tg_ids: config["TELEGRAM_ALLOWED_IDS"] = [n.strip() for n in tg_ids.split(",") if n.strip()]

    if "Slack (requires Bot Token)" in bridges:
        console.print("\n[yellow]💡 Slack Setup Guide:[/yellow]")
        console.print("1. Create an App at https://api.slack.com/apps")
        console.print("2. Add 'Socket Mode' and generate an App-Level Token (xapp-...)")
        console.print("3. In 'OAuth & Permissions', add scopes: app_mentions:read, chat:write, im:write, im:history, channels:history, users:read")
        console.print("4. Install to workspace to get Bot User OAuth Token (xoxb-...)")
        console.print("5. Get Signing Secret from 'Basic Information'\n")

        bot_token = questionary.text("Enter Slack Bot Token (xoxb-...):", 
                                   default=current_config.get("SLACK_BOT_TOKEN", "") if current_config else "").ask()
        if bot_token: 
            config["SLACK_BOT_TOKEN"] = bot_token.strip()
            
            app_token = questionary.password("Enter Slack App Token (xapp-...):", 
                                       default=current_config.get("SLACK_APP_TOKEN", "") if current_config else "").ask()
            if app_token: config["SLACK_APP_TOKEN"] = app_token.strip()
            
            signing_secret = questionary.password("Enter Slack Signing Secret:", 
                                            default=current_config.get("SLACK_SIGNING_SECRET", "") if current_config else "").ask()
            if signing_secret: config["SLACK_SIGNING_SECRET"] = signing_secret.strip()
        
    return config

def setup_autonomous_systems():
    console.print("\n[bold]3. Autonomous Systems Setup[/bold]")
    console.print("[dim]💡 LiteClaw includes background systems that work while you sleep.[/dim]\n")
    
    console.print("[bold cyan]💓 Heartbeat Monitor[/bold cyan]")
    console.print("  - Periodically executes routine tasks defined in HEARTBEAT.md.")
    console.print("  - Default: Every 1 hour.")
    
    console.print("\n[bold cyan]🧠 Subconscious Innovator[/bold cyan]")
    console.print("  - Surfaces random technical insights and experimental tasks.")
    console.print("  - Learns from environment even when you aren't chatting.")
    
    console.print("\n[yellow]Note: You can configure these later by editing HEARTBEAT.md and SUBCONSCIOUS.md in your work directory.[/yellow]")
    
    return True

def pair_bridge(bridge_dir, work_dir, config_data):
    """Start bridge and wait for WhatsApp QR or Telegram bot to capture IDs."""
    console.print("\n[bold]📱 Bridge Pairing & Discovery[/bold]")
    
    platforms_to_pair = []
    if config_data.get("WHATSAPP_TYPE"): platforms_to_pair.append("WhatsApp")
    if config_data.get("TELEGRAM_BOT_TOKEN"): platforms_to_pair.append("Telegram")
    
    qr_mode = "false"
    if "WhatsApp" in platforms_to_pair:
        qr_mode = questionary.select(
            "Select WhatsApp QR Display Mode:",
            choices=[
                questionary.Choice("Standard (Small blocks, cleaner)", value="false"),
                questionary.Choice("Compatible (Large blocks, safer)", value="true")
            ],
            default="false"
        ).ask()
    
    if qr_mode is None: return False, []

    console.print(f"[dim]Starting bridge for {', '.join(platforms_to_pair)}...[/dim]")
    
    env = os.environ.copy()
    env["WORK_DIR"] = work_dir
    env["QR_LARGE"] = qr_mode
    
    # Force UTF-8 for Windows consoles
    if platform.system() == "Windows":
        try:
            subprocess.run(["chcp", "65001"], capture_output=True, shell=(os.name == 'nt'))
            env["PYTHONIOENCODING"] = "utf-8"
        except: pass

    if config_data.get("TELEGRAM_BOT_TOKEN"): env["TELEGRAM_BOT_TOKEN"] = config_data["TELEGRAM_BOT_TOKEN"]
    if config_data.get("TELEGRAM_BOT_TOKENS"): env["TELEGRAM_BOT_TOKENS"] = config_data["TELEGRAM_BOT_TOKENS"]
    if config_data.get("SLACK_BOT_TOKEN"): env["SLACK_BOT_TOKEN"] = config_data["SLACK_BOT_TOKEN"]
    
    try:
        process = subprocess.Popen(
            ["node", "index.js"],
            cwd=bridge_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        
        authenticated = False
        discovered_ids = []
        pin_code = None
        
        while True:
            line = process.stdout.readline()
            if not line: break
            console.print(line, end="")
            
            if "[Bridge] Live QR updated:" in line:
                html_path = os.path.join(work_dir, "qr.html")
                if os.path.exists(html_path):
                    webbrowser.open(f"file:///{html_path}")

            # Platform Readiness Checks
            is_wa_ready = "WhatsApp Client is ready!" in line or "Authenticated successfully!" in line
            is_tg_ready = "Bot started: @" in line
            
            if is_wa_ready or is_tg_ready:
                if is_wa_ready: console.print("\n[bold green]✅ WhatsApp Ready![/bold green]")
                if is_tg_ready: console.print(f"\n[bold green]✅ Telegram Bot Ready![/bold green]")
                
                authenticated = True
                if not pin_code:
                    import random
                    pin_code = f"{random.randint(100000, 999999)}"
                    console.print("\n[bold yellow]🔍 ID Discovery Mode[/bold yellow]")
                    console.print(f"[bold white]Verification PIN: [bold green]{pin_code}[/bold green][/bold white]")
                    console.print(f"\n[yellow]Steps to capture your ID:[/yellow]")
                    console.print(f"1. Open WhatsApp or Telegram")
                    console.print(f"2. Send this PIN to LiteClaw: [bold green]{pin_code}[/bold green]")
                    console.print("\n[dim]⏳ Waiting for PIN... (Press Ctrl+C to skip)[/dim]\n")
                
            # PIN Verification Logic (Shared)
            import re
            # Check for generic format: [Incoming] From Name (ID): Body
            match = re.search(r"From (.+?) \((.+?)\):\s*(.+)", line)
            if match and pin_code:
                sender_name = match.group(1).strip()
                found_id = match.group(2).strip()
                message_body = match.group(3).strip()
                
                if pin_code in message_body:
                    if found_id not in discovered_ids:
                        discovered_ids.append(found_id)
                        console.print(f"\n[bold green]✅ PIN VERIFIED for {sender_name}![/bold green]")
                        console.print(f"[bold green]🎯 ID Captured: {found_id}[/bold green]")
                        
                        if not questionary.confirm("Capture another ID?", default=False).ask():
                            break
                        else:
                            pin_code = f"{random.randint(100000, 999999)}"
                            console.print(f"\n[bold white]Next PIN: [bold green]{pin_code}[/bold green][/bold white]")

            if process.poll() is not None: break
                
        process.terminate()
        return authenticated, discovered_ids
    except Exception as e:
        console.print(f"[red]Error during pairing: {e}[/red]")
        return False, []

def save_config(config_data):
    work_dir = config_data.get("WORK_DIR", ".")
    target_config = os.path.join(work_dir, CONFIG_FILE)
    with open(target_config, "w") as f:
        json.dump(config_data, f, indent=4)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
    console.print(f"\n[bold green]✅ Config saved to {target_config}[/bold green]")

def migrate_files(work_dir):
    configs_dir = os.path.join(work_dir, "configs")
    core_files = ["AGENT.md", "SOUL.md", "PERSONALITY.md", "SUBCONSCIOUS.md", "HEARTBEAT.md"]
    md_files = [f for f in os.listdir(".") if f.endswith(".md")]
    pkg_dir = os.path.dirname(__file__)
    to_copy = []
    for f in md_files: to_copy.append((os.path.join(".", f), os.path.join(configs_dir, f)))
    for cf in core_files:
        pkg_path = os.path.join(pkg_dir, cf)
        if os.path.exists(pkg_path):
            dest = os.path.join(configs_dir, cf)
            if not any(pair[1] == dest for pair in to_copy): to_copy.append((pkg_path, dest))
    
    if to_copy:
        console.print(f"[blue]Copying {len(to_copy)} files to {configs_dir}...[/blue]")
        for src, dest in to_copy:
            try:
                if os.path.exists(src):
                    shutil.copy2(src, dest)
                    console.print(f"  [dim]Copied {os.path.basename(src)}[/dim]")
            except Exception as e:
                console.print(f"  [red]Failed to copy {os.path.basename(src)}: {e}[/red]")

def onboarding():
    clear_screen()
    console.print(Panel.fit("[bold cyan]🦞 LiteClaw - Adaptive AI Gateway[/bold cyan]\n[dim]Onboarding Wizard[/dim]", border_style="cyan"))
    
    node_ok, vision_ok = check_system_dependencies()
    
    # Check for existing config to preload
    current_config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f: current_config = json.load(f)
        except: pass

    work_dir = setup_work_dir(current_config)
    if not work_dir: return
    
    llm_config = setup_llm(current_config)
    if not llm_config: return
    
    vision_config = setup_vision_llm(current_config, llm_config)
    llm_config.update(vision_config)
    
    bridge_config = setup_bridges(current_config)
    if bridge_config is None: return

    setup_autonomous_systems()

    config_data = {**llm_config, **bridge_config, "WORK_DIR": work_dir}
    
    if questionary.confirm("Save and Finish?").ask():
        save_config(config_data)
        migrate_files(work_dir)
        
        platforms_to_pair = []
        if config_data.get("WHATSAPP_TYPE"): platforms_to_pair.append("WhatsApp")
        if config_data.get("TELEGRAM_BOT_TOKEN"): platforms_to_pair.append("Telegram")
        
        bridge_dir = os.path.join(os.path.dirname(__file__), "bridge")
        if not os.path.exists(bridge_dir): bridge_dir = os.path.join(os.getcwd(), "src", "liteclaw", "bridge")
        
        if platforms_to_pair:
            if os.path.exists(bridge_dir) and not os.path.exists(os.path.join(bridge_dir, "node_modules")):
                console.print("[blue]Pre-installing Bridge Dependencies...[/blue]")
                subprocess.check_call(["npm", "install"], cwd=bridge_dir, shell=(os.name == 'nt'))
            
            if questionary.confirm(f"\nPair {', '.join(platforms_to_pair)} now?", default=True).ask():
                auth_ok, discovered_ids = pair_bridge(bridge_dir, work_dir, config_data)
                if auth_ok and discovered_ids:
                    # Merge discovered IDs into config
                    wa_allowed = config_data.get("WHATSAPP_ALLOWED_NUMBERS", [])
                    tg_allowed = config_data.get("TELEGRAM_ALLOWED_IDS", [])
                    
                    for d_id in discovered_ids:
                        if ":" in d_id: # Telegram ID format "username:chatId"
                            if d_id not in tg_allowed: tg_allowed.append(d_id)
                        else: # WhatsApp ID format
                            if d_id not in wa_allowed: wa_allowed.append(d_id)
                    
                    config_data["WHATSAPP_ALLOWED_NUMBERS"] = wa_allowed
                    config_data["TELEGRAM_ALLOWED_IDS"] = tg_allowed
                    
                    # Save updated config
                    save_config(config_data)

        console.print("\n[bold white]🚀 Ready! Run: liteclaw run[/bold white]")

if __name__ == "__main__":
    onboarding()
