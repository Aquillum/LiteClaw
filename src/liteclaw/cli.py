import click
import uvicorn
import os
import subprocess
import json
import shutil
import requests
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.text import Text

console = Console()

@click.group()
def cli():
    """
    \b
    🦞 LiteClaw - Adaptive AI Gateway & Agent
    
    A sophisticated bridge between LLMs and your world (WhatsApp, Shell, Browser).
    This CLI allows you to start the gateway, onboard, or jump into a live session.
    """
    pass

@cli.command()
def onboard():
    """✨ Run the setup wizard (API Keys, Bridge Config)"""
    from .onboarding import onboarding as run_onboarding
    run_onboarding()

@cli.command()
@click.option('--port', default=8009, help='Server port')
@click.option('--host', default='0.0.0.0', help='Server host')
@click.option('--no-bridge', is_flag=True, help='Skip starting the Node bridge')
def run(port, host, no_bridge):
    """🚀 Start the LiteClaw Gateway (FastAPI + Bridge)"""
    import platform
    
    # 0. Check Configuration - look in multiple locations
    config_locations = [
        os.path.join(os.getcwd(), "config.json"),  # Current directory
        r"C:\liteclaw\config.json" if platform.system() == "Windows" else os.path.expanduser("~/liteclaw/config.json"),  # Default WORK_DIR
    ]
    
    config_path = None
    for loc in config_locations:
        if os.path.exists(loc):
            config_path = loc
            break
    
    if not config_path:
        console.print(Panel.fit("[bold red]❌ Configuration File Not Found![/bold red]\n\nYou must run the onboarding wizard first.", border_style="red"))
        console.print("Run this command to set up:\n[bold yellow]liteclaw onboard[/bold yellow]")
        return

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            if not config.get("LLM_API_KEY"):
                console.print(Panel.fit("[bold red]❌ LLM API Key Missing![/bold red]\n\nYour configuration is incomplete.", border_style="red"))
                console.print("Run this command to fix it:\n[bold yellow]liteclaw onboard[/bold yellow]")
                return
    except Exception as e:
        console.print(f"[red]Error reading config.json: {e}[/red]")
        return
    
    console.print(f"[dim]Loaded config from: {config_path}[/dim]")
    console.print(Panel.fit(f"[bold green]🚀 Launching LiteClaw Gateway[/bold green]\nHost: {host}\nPort: {port}"))
    
    # 1. Locate the Bridge Directory
    pkg_bridge = os.path.join(os.path.dirname(__file__), "bridge")
    cwd_bridge = os.path.join(os.getcwd(), "src", "liteclaw", "bridge")
    
    bridge_dir = None
    if os.path.exists(os.path.join(pkg_bridge, "index.js")):
        bridge_dir = pkg_bridge
    elif os.path.exists(os.path.join(cwd_bridge, "index.js")):
        bridge_dir = cwd_bridge
    
    if not no_bridge:
        if bridge_dir:
            console.print(f"[dim]  > Found bridge at: {bridge_dir}[/dim]")
            
            # 2. Check for Node.js
            if not shutil.which("node") and not shutil.which("node.exe"):
                 console.print("[bold red]  ❌ Error: Node.js is not installed. Bridge cannot start.[/bold red]")
            else:
                # 3. Check for dependencies
                node_modules = os.path.join(bridge_dir, "node_modules")
                if not os.path.isdir(node_modules):
                    console.print("[yellow]  > First run detected. Installing Node dependencies...[/yellow]")
                    try:
                        subprocess.check_call(["npm", "install"], cwd=bridge_dir)
                        console.print("[green]  ✅ Dependencies installed.[/green]")
                    except subprocess.CalledProcessError:
                         console.print("[red]  ❌ Failed to run 'npm install'.[/red]")

                # 4. Start Bridge
                console.print("[blue]  > Starting Node Bridge (WhatsApp/Telegram/Slack)...[/blue]")
                
                env = os.environ.copy()
                env["PYTHON_BACKEND_PORT"] = str(port)
                
                # Load config to pass secrets to bridge via env
                config_path = os.path.join(os.getcwd(), "config.json")
                if os.path.exists(config_path):
                    try:
                        with open(config_path) as f:
                            data = json.load(f)
                            if data.get("TELEGRAM_BOT_TOKEN"):
                                env["TELEGRAM_BOT_TOKEN"] = data["TELEGRAM_BOT_TOKEN"]
                            if data.get("SLACK_BOT_TOKEN"):
                                env["SLACK_BOT_TOKEN"] = data["SLACK_BOT_TOKEN"]
                            if data.get("WORK_DIR"):
                                env["WORK_DIR"] = data["WORK_DIR"]
                    except:
                        pass
                
                subprocess.Popen(["node", "index.js"], cwd=bridge_dir, env=env)
        else:
            console.print("[yellow]  ⚠️ Bridge directory not found. Running Python backend only.[/yellow]")

    # Start FastAPI server
    uvicorn.run("liteclaw.main:app", host=host, port=port, reload=True)

@cli.command()
def configure():
    """🔧 Selectively update configuration (LLM, Bridges, WorkDir)"""
    from .onboarding import setup_llm, setup_bridges, setup_work_dir, save_config, PROVIDERS
    
    config_path = os.path.join(os.getcwd(), "config.json")
    current_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path) as f: current_config = json.load(f)
        except: pass

    choices = [
        "LLM Settings (Provider, Model, API Key)",
        "Messaging Bridges (WhatsApp, Telegram, Slack)",
        "Work Directory",
        "Exit"
    ]
    
    while True:
        task = questionary.select("What would you like to configure?", choices=choices).ask()
        if not task or task == "Exit": break
        
        if "LLM" in task:
            new_llm = setup_llm(current_config)
            if new_llm:
                current_config.update(new_llm)
                save_config(current_config)
        
        elif "Bridges" in task:
            new_bridges = setup_bridges(current_config)
            if new_bridges is not None:
                # Remove old bridge keys if they were deselected (simplified)
                for key in ["TELEGRAM_BOT_TOKEN", "SLACK_BOT_TOKEN", "WHATSAPP_TYPE", "WHATSAPP_ALLOWED_NUMBERS"]:
                    if key in current_config: del current_config[key]
                current_config.update(new_bridges)
                save_config(current_config)
                
        elif "Work Directory" in task:
            new_dir = setup_work_dir(current_config)
            if new_dir:
                current_config["WORK_DIR"] = new_dir
                save_config(current_config)

@cli.command()
def pair():
    """📱 Pair WhatsApp via QR Code"""
    from .onboarding import pair_whatsapp
    
    config_path = os.path.join(os.getcwd(), "config.json")
    if not os.path.exists(config_path):
        console.print("[red]No config.json found. Please run 'liteclaw onboard' first.[/red]")
        return
        
    with open(config_path) as f:
        config = json.load(f)
        
    bridge_dir = os.path.join(os.path.dirname(__file__), "bridge")
    if not os.path.exists(bridge_dir):
        bridge_dir = os.path.join(os.getcwd(), "src", "liteclaw", "bridge")
        
    pair_whatsapp(bridge_dir, config.get("WORK_DIR", "."), config)

@cli.command()
@click.option('--host', default='http://localhost:8009', help='Gateway URL')
def console_cli(host):
    """💻 Interactive CLI Console (Requires running Gateway)"""
    
    # 1. Check connection
    try:
        resp = requests.get(f"{host}/")
        if resp.status_code != 200:
             console.print(f"[red]Gateway at {host} is running but returned {resp.status_code}.[/red]")
             return
    except requests.exceptions.ConnectionError:
        console.print(Panel.fit(
            f"[bold red]❌ Cannot connect to LiteClaw Gateway at {host}[/bold red]\n\n"
            "Please run [bold]liteclaw run[/bold] in a separate terminal first.",
            title="Connection Error"
        ))
        return

    # 2. List Sessions
    try:
        resp = requests.get(f"{host}/sessions/list")
        sessions = resp.json()
    except Exception as e:
        console.print(f"[red]Failed to fetch sessions: {e}[/red]")
        return
        
    console.clear()
    console.print(Panel.fit("[bold blue]🦞 LiteClaw Interactive CLI[/bold blue]", border_style="blue"))
    
    if not sessions:
        console.print("[yellow]No active sessions found.[/yellow]")
        if Prompt.ask("Create a new session?", choices=["y", "n"]) == "y":
            sid = Prompt.ask("Enter new Session ID (e.g. 'cli_user')")
            requests.post(f"{host}/session/create", json={"session_id": sid})
            current_session = sid
        else:
            return
    else:
        table = Table(title="Active Sessions")
        table.add_column("Index", style="cyan")
        table.add_column("Session ID", style="magenta")
        table.add_column("Created", style="dim")
        
        for idx, s in enumerate(sessions):
            table.add_row(str(idx + 1), s['session_id'], str(s.get('created_at', 'N/A')))
            
        console.print(table)
        
        choice = Prompt.ask("Select Session Index (or 'n' for new)", default="1")
        if choice.lower() == 'n':
            sid = Prompt.ask("Enter new Session ID")
            requests.post(f"{host}/session/create", json={"session_id": sid})
            current_session = sid
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sessions):
                    current_session = sessions[idx]['session_id']
                else:
                    console.print("[red]Invalid index.[/red]")
                    return
            except:
                console.print("[red]Invalid input.[/red]")
                return

    # 3. Chat Loop
    console.clear()
    console.print(Panel(f"Connected to session: [bold green]{current_session}[/bold green]\nType 'exit' to quit.", title="💬 Chat Active"))
    
    while True:
        try:
            user_input = Prompt.ask(f"[bold cyan]You[/bold cyan]")
            if user_input.strip().lower() in ['exit', 'quit']:
                break
                
            # Send to API
            with console.status("[bold green]LiteClaw is thinking...[/bold green]"):
                try:
                    # We use the non-streaming endpoint for simplicity in CLI for now
                    resp = requests.post(f"{host}/chat", json={
                        "message": user_input,
                        "session_id": current_session,
                        "stream": False
                    })
                    data = resp.json()
                    reply = data.get("response", "")
                    
                    console.print(f"[bold magenta]LiteClaw[/bold magenta]: {reply}")
                    console.print(f"[dim]--------------------------------------------------[/dim]")
                    
                except Exception as e:
                    console.print(f"[red]Error sending message: {e}[/red]")
                    
        except KeyboardInterrupt:
            break
            
    console.print("\n[blue]Goodbye![/blue]")

import questionary # Added import locally for the commands

def main():
    cli()

if __name__ == '__main__':
    main()
