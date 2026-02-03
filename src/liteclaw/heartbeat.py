import time
import threading
import os
import yaml
import re
from typing import List, Dict, Any
from .agent import LiteClawAgent
from .config import settings

HEARTBEAT_FILE = os.path.join(settings.get_configs_dir(), "HEARTBEAT.md")
HEARTBEAT_SESSION_ID = "soul-heartbeat-monitor"

class HeartbeatMonitor:
    def __init__(self):
        self._running = False
        self._thread = None
        self._agent = LiteClawAgent()
        self._last_run = 0
        self._config = {
            "interval_seconds": 240,
            "enabled": False
        }
        self._tasks = []

    def _parse_heartbeat_file(self):
        """Parse the HEARTBEAT.md file for config and tasks."""
        if not os.path.exists(HEARTBEAT_FILE):
            return

        try:
            with open(HEARTBEAT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split frontmatter and content
            parts = content.split('---')
            if len(parts) >= 3:
                # Parse frontmatter
                try:
                    yaml_config = yaml.safe_load(parts[1])
                    if yaml_config:
                        self._config.update(yaml_config)
                except Exception as e:
                    print(f"[Heartbeat] ⚠️ YAML error: {e}")

                # Parse tasks from markdown list
                body = parts[2]
                # improved regex to capture bullet points (- or *)
                tasks = re.findall(r'^[\-\*]\s+(.+)$', body, re.MULTILINE)
                self._tasks = [t.strip() for t in tasks if t.strip()]
            
        except Exception as e:
            print(f"[Heartbeat] ❌ Error parsing file: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Heartbeat] ❤️ Monitor started via HEARTBEAT.md")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[Heartbeat] Monitor stopped")

    def _loop(self):
        while self._running:
            self._parse_heartbeat_file()
            
            if not self._config.get("enabled", False):
                time.sleep(30) # Check config every 30s if disabled
                continue

            interval = self._config.get("interval_seconds", 3600)
            now = time.time()

            if now - self._last_run >= interval:
                if self._tasks:
                    print(f"[Heartbeat] 💓 Pulse! Executing {len(self._tasks)} tasks...")
                    self._execute_pulse()
                self._last_run = time.time()
            
            time.sleep(10) # Minimal sleep to prevent busy loop

    def _execute_pulse(self):
        """Execute the defined tasks using the agent."""
        if not self._tasks:
            return

        # Combine tasks into a single prompt for efficiency
        task_list = "\n".join([f"- {t}" for t in self._tasks])
        prompt = f"""
[HEARTBEAT SYSTEM TRIGGER]
This is an automated productivity pulse based on user preferences.
Please execute the following routine tasks:

{task_list}

Verify their status and report purely on the outcomes. 
If a task requires no action (e.g. no new logs), allow it to pass.
"""
        try:
            # We run this in the background, output goes to logs/notification system
            # Since this is "fire and forget" for the loop, we just trigger it.
            # Ideally, we want to notify the user of the result.
            print(f"[Heartbeat] Sending prompt to agent...")
            
            # Using process_message synchronously in this thread
            response = self._agent.process_message(
                prompt, 
                session_id=HEARTBEAT_SESSION_ID,
                platform="heartbeat" # Special platform for routing
            )
            
            print(f"[Heartbeat] ✅ Cycle Complete. Result summary length: {len(response)}")
            
            # TODO: We could push this notification to the user's phone if configured
            
        except Exception as e:
            print(f"[Heartbeat] ❌ Execution failed: {e}")

heartbeat = HeartbeatMonitor()
