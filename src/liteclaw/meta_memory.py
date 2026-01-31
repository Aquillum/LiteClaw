import os

AGENT_FILE = os.path.abspath("AGENT.md")
SOUL_FILE = os.path.abspath("SOUL.md")

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
