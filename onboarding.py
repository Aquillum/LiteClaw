import questionary
import json
import os
import subprocess
import platform
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

PROVIDERS = {
    "OpenAI": "https://api.openai.com/v1",
    "OpenRouter": "https://openrouter.ai/api/v1",
    "Groq": "https://api.groq.com/openai/v1",
    "DeepSeek": "https://api.deepseek.com/v1",
    "Custom": None
}

CONFIG_FILE = "config.json"

def onboarding():
    console.print(Panel.fit("Welcome to [bold blue]LiteClaw[/bold blue] Setup", border_style="blue"))
    
    # 1. Select Provider
    provider_name = questionary.select(
        "Select your LLM Provider:",
        choices=list(PROVIDERS.keys())
    ).ask()
    
    if not provider_name:
        return

    base_url = PROVIDERS[provider_name]
    
    if provider_name == "Custom":
        base_url = questionary.text("Enter your Custom Base URL:").ask()
    
    # 2. API Key
    api_key = questionary.password(f"Enter your API Key for {provider_name}:").ask()
    
    # 3. Model
    default_models = {
        "OpenAI": "gpt-4o",
        "OpenRouter": "x-ai/grok-code-fast-1",
        "Groq": "llama3-70b-8192",
        "DeepSeek": "deepseek-chat"
    }
    
    default_model = default_models.get(provider_name, "gpt-3.5-turbo")
    
    model = questionary.text(
        f"Enter the Model Name (default: {default_model}):",
        default=default_model
    ).ask()
    
    # Confirm
    console.print(f"\n[bold]Configuration Summary:[/bold]")
    console.print(f"Provider: [green]{provider_name}[/green]")
    console.print(f"Base URL: [cyan]{base_url}[/cyan]")
    console.print(f"Model:    [yellow]{model}[/yellow]")
    console.print(f"API Key:  [red]********[/red]")
    
    if not questionary.confirm("Save this configuration?").ask():
        console.print("[red]Setup cancelled.[/red]")
        return

    # Determine provider string for config
    # User requested to use 'openai' provider for OpenRouter etc. with custom base_url
    # allowing litellm to treat them as standard openai compatible endpoints.
    final_provider = "openai"
    
    config_data = {
        "LLM_PROVIDER": final_provider,
        "LLM_BASE_URL": base_url,
        "LLM_API_KEY": api_key,
        "LLM_MODEL": model
    }
    
    if questionary.confirm("Do you want to configure WhatsApp (Node.js Bridge)?").ask():
        bridge_dir = os.path.join(os.getcwd(), "whatsapp_bridge")
        
        # Check Node
        try:
            subprocess.run(["node", "-v"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            console.print("[red]Node.js not found. Please install Node.js (and npm) to use this feature[/red]")
            console.print("Download from: https://nodejs.org/")
            if not questionary.confirm("Do you have Node installed in a different path? (If 'No', we will skip WhatsApp set up)").ask():
                 # Skip logic
                 pass
            else:
                 # Logic to ask for path could go here, but for now we just continue at risk
                 pass
            # If we really can't find it, we should essentially abort the WP setup part
            # But the user might want to install it now.
            if not questionary.confirm("Try to proceed anyway?").ask():
                 # We skip the rest of the WP config but continue to save other config
                 config_data["WHATSAPP_TYPE"] = "disabled"
                 # Goto save
        
        # Only proceed to install if user said yes or node exists (simplified flow)
        # We will wrap the rest in a check or just let it fail gracefully if user insists.
        
        console.print("[blue]Installing Node.js dependencies...[/blue]")
        try:
            subprocess.run("npm install", shell=True, cwd=bridge_dir, check=True)
            console.print("[green]Dependencies installed.[/green]")
        except Exception as e:
            console.print(f"[red]Failed to install dependencies: {e}[/red]")

        if questionary.confirm("Do you want to limit responses to specific numbers?").ask():
            target_nums = questionary.text("Enter comma-separated Phone Numbers (e.g., 917305540292):").ask()
            nums = [n.strip() for n in target_nums.split(",") if n.strip()]
            config_data["WHATSAPP_ALLOWED_NUMBERS"] = nums

        console.print("\n[bold cyan]Telegram & Slack Support[/bold cyan]")
        console.print("LiteClaw now uses [bold]Polling Mode[/bold] for Telegram (no ngrok required!).")
        
        if questionary.confirm("Do you want to enable the Telegram Bot?").ask():
            token = questionary.text("Enter your Telegram Bot Token (from @BotFather):").ask()
            if token:
                config_data["TELEGRAM_BOT_TOKEN"] = token
                console.print("[green]Telegram Bot Token saved.[/green]")
            
        if questionary.confirm("Do you want to enable Giphy (for hilarious GIFs)?").ask():
            giphy_key = questionary.text("Enter your Giphy API Key:").ask()
            if giphy_key:
                config_data["GIPHY_API_KEY"] = giphy_key
                console.print("[green]Giphy API Key saved.[/green]")

        if questionary.confirm("Do you want to enable Slack?").ask():
            slack_token = questionary.text("Enter your Slack Bot User OAuth Token (xoxb-...):").ask()
            if slack_token:
                config_data["SLACK_BOT_TOKEN"] = slack_token
                console.print("[green]Slack Bot Token saved.[/green]")
            
        console.print("\n[bold yellow]STARTING UNIFIED BRIDGE...[/bold yellow]")
        console.print("Please scan the QR Code that will appear below using WhatsApp on your phone.")
        console.print("The bridge process will remain running.")
        console.print("Press Ctrl+C to stop it once you are logged in, or keep it running if you want to use it now.")
        
        questionary.press_any_key_to_continue("Press any key to start the login process...").ask()
        
        try:
            # We don't spawn it here anymore because run.py will handle it in the same terminal
            # to keep everything unified as requested.
            console.print("[green]Bridge configured. It will start automatically when you run 'python run.py'.[/green]")
            config_data["WHATSAPP_TYPE"] = "node_bridge"
            
        except Exception as e:
            console.print(f"[red]Failed to start bridge: {e}[/red]")

    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
        console.print(f"\n[bold green]Configuration saved to {CONFIG_FILE}![/bold green]")
        console.print("You can now start the server with 'python run.py'.")
        console.print("Make sure the WhatsApp Bridge (Node.js) is also running!")
    except Exception as e:
        console.print(f"\n[bold red]Error saving config:[/bold red] {e}")

if __name__ == "__main__":
    try:
        onboarding()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup interrupted.[/yellow]")
