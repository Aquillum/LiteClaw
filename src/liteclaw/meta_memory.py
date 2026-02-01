from .config import settings
import os

def get_file_path(filename: str) -> str:
    """Gets the path for a meta-memory file, prioritizing the WORK_DIR/configs folder."""
    # 1. Try WORK_DIR/configs
    work_path = os.path.join(settings.get_configs_dir(), filename)
    if os.path.exists(work_path):
        return work_path
        
    # 2. Try the parent directory of this file (legacy location)
    legacy_path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(legacy_path):
        return legacy_path
        
    # 3. Default to WORK_DIR/configs for new files
    return work_path

AGENT_FILE = get_file_path("AGENT.md")
SOUL_FILE = get_file_path("SOUL.md")
PERSONALITY_FILE = get_file_path("PERSONALITY.md")

def read_file_content(filepath):
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def get_agent_profile():
    return read_file_content(AGENT_FILE)

def get_soul_memory():
    return read_file_content(SOUL_FILE)

def get_personality_memory():
    return read_file_content(PERSONALITY_FILE)

def update_soul_memory(content: str):
    """
    Overwrites SOUL.md with new content. 
    The AI should rewrite the whole file or append intelligently. 
    For simplicity, we'll let the AI pass the full new content or appended logs.
    But usually, the AI should read -> modify -> write.
    """
    try:
        with open(SOUL_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return "SOUL updated successfully."
    except Exception as e:
        return f"Failed to update SOUL: {e}"

def append_to_soul(content: str):
    try:
        with open(SOUL_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{content}")
        return "Memory appended to SOUL."
    except Exception as e:
        return f"Failed to append to SOUL: {e}"

def update_personality_memory(content: str):
    """
    Overwrites PERSONALITY.md with new content.
    """
    try:
        with open(PERSONALITY_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return "Personality updated successfully."
    except Exception as e:
        return f"Failed to update Personality: {e}"
