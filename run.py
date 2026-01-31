import uvicorn
import os

if __name__ == "__main__":
    # Ensure src is in python path if running directly
    
    # Optional: Start Node Bridge in same terminal if it exists
    bridge_path = os.path.join(os.getcwd(), "whatsapp_bridge", "index.js")
    if os.path.exists(bridge_path):
        import subprocess
        import json
        
        # Load config to get keys
        env = os.environ.copy()
        try:
            with open("config.json") as f:
                data = json.load(f)
                if data.get("TELEGRAM_BOT_TOKEN"):
                    env["TELEGRAM_BOT_TOKEN"] = data["TELEGRAM_BOT_TOKEN"]
                if data.get("SLACK_BOT_TOKEN"):
                    env["SLACK_BOT_TOKEN"] = data["SLACK_BOT_TOKEN"]
        except:
            pass
            
        print("Starting unified Node Bridge (WhatsApp/Telegram/Slack)...")
        # Run node in background but piping output to this console
        subprocess.Popen(["node", bridge_path], cwd=os.path.join(os.getcwd(), "whatsapp_bridge"), env=env)

    uvicorn.run("src.liteclaw.main:app", host="0.0.0.0", port=8009)
