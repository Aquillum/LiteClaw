import uvicorn
import os

if __name__ == "__main__":
    # Ensure src is in python path if running directly
    
    # Optional: Start Node Bridge in same terminal if it exists
    bridge_search_paths = [
        os.path.join(os.getcwd(), "whatsapp_bridge"),
        os.path.join(os.getcwd(), "src", "liteclaw", "bridge")
    ]
    
    bridge_dir = next((p for p in bridge_search_paths if os.path.exists(os.path.join(p, "index.js"))), None)
    
    if bridge_dir:
        bridge_path = os.path.join(bridge_dir, "index.js")
        import subprocess
        import json
        
        # Load config to get keys
        env = os.environ.copy()
        try:
            # Check for config.json
            config_paths = ["config.json", os.path.join(bridge_dir, "..", "config.json")]
            for cp in config_paths:
                if os.path.exists(cp):
                    with open(cp) as f:
                        data = json.load(f)
                        if data.get("TELEGRAM_BOT_TOKEN"):
                            env["TELEGRAM_BOT_TOKEN"] = data["TELEGRAM_BOT_TOKEN"]
                        if data.get("SLACK_BOT_TOKEN"):
                            env["SLACK_BOT_TOKEN"] = data["SLACK_BOT_TOKEN"]
                        if data.get("SLACK_APP_TOKEN"):
                            env["SLACK_APP_TOKEN"] = data["SLACK_APP_TOKEN"]
                        if data.get("SLACK_SIGNING_SECRET"):
                            env["SLACK_SIGNING_SECRET"] = data["SLACK_SIGNING_SECRET"]
                        break
        except:
            pass
            
        print(f"Starting unified Node Bridge from {bridge_dir}...")
        # Run node in background but piping output to this console
        subprocess.Popen(["node", "index.js"], cwd=bridge_dir, env=env)

    uvicorn.run("src.liteclaw.main:app", host="0.0.0.0", port=8009)
