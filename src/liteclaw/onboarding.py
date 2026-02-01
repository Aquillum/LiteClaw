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

PROVIDERS = {
    "OpenAI": {
        "base": "https://api.openai.com/v1", 
        "models": ["gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo"]
    },
    "OpenRouter": {
        "base": "https://openrouter.ai/api/v1",
        "models": ["anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5", "mistralai/mixtral-8x22b", "openai/gpt-4o"]
    },
    "Groq": {
        "base": "https://api.groq.com/openai/v1",
        "models": ["llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"]
    },
    "DeepSeek": {
        "base": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"]
    },
    "Custom (Ollama/Local)": {
        "base": "http://localhost:11434/v1",
        "models": ["llama3", "mistral", "qwen"]
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

def setup_llm(current_config=None):
    console.print("\n[bold]1. LLM Provider Setup[/bold]")
    
    default_provider = "OpenRouter"
    if current_config and current_config.get("LLM_BASE_URL"):
        # Reverse lookup or just use default
        pass

    provider_name = questionary.select("Select LLM Provider:", choices=list(PROVIDERS.keys()), default=default_provider).ask()
    if not provider_name: return None

    base_url = PROVIDERS[provider_name]["base"]
    if provider_name == "Custom (Ollama/Local)":
        base_url = questionary.text("Enter Base URL:", default=current_config.get("LLM_BASE_URL", base_url)).ask()
        if base_url is None: return None

    mode_choices = PROVIDERS[provider_name].get("models", []) + ["Input Custom Model Name"]
    default_model = current_config.get("LLM_MODEL") if current_config else None
    
    model = questionary.select("Select Model:", choices=mode_choices, default=default_model if default_model in mode_choices else None).ask()
    if model is None: return None
    if model == "Input Custom Model Name":
        model = questionary.text("Enter Model Name:", default=default_model or "").ask()
        if model is None: return None

    api_key = "sk-placeholder"
    if provider_name != "Custom (Ollama/Local)":
        api_key_input = questionary.password(f"Enter API Key for {provider_name}:", default=current_config.get("LLM_API_KEY", "") if current_config else "").ask()
        if api_key_input is None: return None
        api_key = api_key_input.strip()

    return {
        "LLM_PROVIDER": provider_name,
        "LLM_BASE_URL": base_url,
        "LLM_API_KEY": api_key,
        "LLM_MODEL": model
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
        limit = questionary.confirm("Limit WhatsApp numbers?", default=bool(current_config.get("WHATSAPP_ALLOWED_NUMBERS") if current_config else True)).ask()
        if limit:
            existing = ",".join(current_config.get("WHATSAPP_ALLOWED_NUMBERS", [])) if current_config else ""
            nums = questionary.text("Allowed Numbers (comma-sep):", default=existing).ask()
            if nums: config["WHATSAPP_ALLOWED_NUMBERS"] = [n.strip() for n in nums.split(",") if n.strip()]

    if "Telegram (requires Bot Token)" in bridges:
        token = questionary.text("Enter TG Token:", default=current_config.get("TELEGRAM_BOT_TOKEN", "") if current_config else "").ask()
        if token: config["TELEGRAM_BOT_TOKEN"] = token

    if "Slack (requires Bot Token)" in bridges:
        token = questionary.text("Enter Slack Token:", default=current_config.get("SLACK_BOT_TOKEN", "") if current_config else "").ask()
        if token: config["SLACK_BOT_TOKEN"] = token
        
    return config

def pair_whatsapp(bridge_dir, work_dir, config_data):
    """Start bridge and wait for WhatsApp QR login during onboarding."""
    console.print("\n[bold]📱 WhatsApp Pairing[/bold]")
    
    qr_mode = questionary.select(
        "Select QR Display Mode:",
        choices=[
            questionary.Choice("Standard (Small blocks, cleaner if terminal supports it)", value="false"),
            questionary.Choice("Compatible (Large blocks, safer for older terminals)", value="true")
        ],
        default="false"
    ).ask()
    
    if qr_mode is None: return False

    console.print("[dim]Starting bridge to generate QR code...[/dim]")
    
    env = os.environ.copy()
    env["WORK_DIR"] = work_dir
    env["QR_LARGE"] = qr_mode
    
    # Force UTF-8 for Windows consoles
    if platform.system() == "Windows":
        try:
            subprocess.run(["chcp", "65001"], shell=True, capture_output=True)
            env["PYTHONIOENCODING"] = "utf-8"
        except: pass

    if config_data.get("TELEGRAM_BOT_TOKEN"):
        env["TELEGRAM_BOT_TOKEN"] = config_data["TELEGRAM_BOT_TOKEN"]
    
    try:
        process = subprocess.Popen(
            ["node", "index.js"],
            cwd=bridge_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8", # Explicitly use utf-8 for reading
            bufsize=1,
        )
        
        console.print("[yellow]Waiting for QR code... (this may take 10-20s)[/yellow]")
        console.print("[dim]If the QR is still broken, look for 'qr.html' in your work directory.[/dim]")
        
        authenticated = False
        
        while True:
            line = process.stdout.readline()
            if not line: break
            
            # Use RICH to print line, handles UTF8 better
            console.print(line, end="")
            
            if "[Bridge] Live QR updated:" in line or "[Bridge] Fallback QR saved to:" in line:
                html_path = os.path.join(work_dir, "qr.html")
                if os.path.exists(html_path):
                    console.print(f"[bold cyan]🔗 Opening QR Code in browser...[/bold cyan]")
                    webbrowser.open(f"file:///{html_path}")

            if "WhatsApp Client is ready!" in line or "Authenticated successfully!" in line:
                authenticated = True
                console.print("\n[bold green]✅ WhatsApp Paired Successfully![/bold green]")
                break
            
            if process.poll() is not None: break
                
        time.sleep(2)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            
        return authenticated
        
    except Exception as e:
        console.print(f"[red]Error during WhatsApp pairing: {e}[/red]")
        return False

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
    core_files = ["AGENT.md", "SOUL.md", "PERSONALITY.md"]
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
    
    bridge_config = setup_bridges(current_config)
    if bridge_config is None: return

    config_data = {**llm_config, **bridge_config, "WORK_DIR": work_dir}
    
    if questionary.confirm("Save and Finish?").ask():
        save_config(config_data)
        migrate_files(work_dir)
        
        bridge_dir = os.path.join(os.path.dirname(__file__), "bridge")
        if not os.path.exists(bridge_dir): bridge_dir = os.path.join(os.getcwd(), "src", "liteclaw", "bridge")
        
        if "WhatsApp (requires phone scan)" in bridge_config.get("WHATSAPP_TYPE", "") or config_data.get("WHATSAPP_TYPE"):
            if os.path.exists(bridge_dir) and not os.path.exists(os.path.join(bridge_dir, "node_modules")):
                console.print("[blue]Pre-installing Bridge Dependencies...[/blue]")
                subprocess.check_call(["npm", "install"], cwd=bridge_dir, shell=True)
            
            if questionary.confirm("\nPair WhatsApp via QR now?", default=True).ask():
                pair_whatsapp(bridge_dir, work_dir, config_data)

        console.print("\n[bold white]🚀 Ready! Run: liteclaw run[/bold white]")

if __name__ == "__main__":
    onboarding()
