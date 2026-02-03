import subprocess
import platform
import os
import tempfile
import uuid
import re

# === CRITICAL SECURITY LAYER ===
# Commands that would terminate the agent itself or damage the system
BLOCKED_COMMAND_PATTERNS = [
    # Self-termination patterns
    r"taskkill.*python",
    r"taskkill.*node",
    r"taskkill.*liteclaw",
    r"kill.*python",
    r"kill.*node",
    r"pkill.*python",
    r"pkill.*node",
    r"killall.*python",
    r"killall.*node",
    r"stop-process.*python",
    r"stop-process.*node",
    
    # System destruction patterns
    r"rm\s+-rf\s+/",
    r"rmdir\s+/s\s+/q\s+c:",
    r"del\s+/f\s+/s\s+/q\s+c:",
    r"format\s+c:",
    r"shutdown\s+/(s|r|h)",
    r"shutdown\s+-(h|r|P)",
    
    # Registry/System corruption
    r"reg\s+delete.*hklm",
    r"reg\s+delete.*hkcu",
    
    # Network attacks
    r"netsh.*firewall.*disable",
]

def is_command_safe(command: str) -> tuple[bool, str]:
    """Check if a command is safe to execute."""
    cmd_lower = command.lower()
    
    for pattern in BLOCKED_COMMAND_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return False, f"🚫 BLOCKED: Command matches dangerous pattern '{pattern}'. Self-termination and destructive commands are not allowed."
    
    return True, ""

def execute_command(command: str) -> str:
    """
    Executes a shell command on the local system.
    Automatically detects complex commands and writes them to temp files to avoid WinError 267.
    
    SECURITY: Commands that would terminate the agent or damage the system are blocked.
    
    Args:
        command: The command to execute.
        
    Returns:
        The output of the command or error message.
    """
    # === SECURITY CHECK ===
    is_safe, block_reason = is_command_safe(command)
    if not is_safe:
        return block_reason
    
    try:
        system = platform.system()
        project_root = r"d:\openclaw_lite"
        
        # Create project_root if it doesn't exist
        os.makedirs(project_root, exist_ok=True)
        
        if system == "Windows":
            # Detect complex commands that will fail with WinError 267
            complexity_indicators = [
                '@{',           # PowerShell hashtables
                '| ConvertTo-Json',  # JSON conversion
                'Invoke-RestMethod', # Web requests
                'Invoke-WebRequest',
                'try {',        # Try-catch blocks
                len(command) > 200,  # Very long commands
                command.count('"') > 4,  # Many nested quotes
                command.count("'") > 4,
            ]
            
            is_complex = any(complexity_indicators)
            
            if is_complex:
                # Write to temp file and execute
                temp_script = os.path.join(project_root, f"temp_{uuid.uuid4().hex[:8]}.ps1")
                with open(temp_script, 'w', encoding='utf-8') as f:
                    f.write(command)
                
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_script],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=project_root
                )
                
                # Clean up temp file
                try:
                    os.remove(temp_script)
                except:
                    pass
            else:
                # Simple command - execute inline
                result = subprocess.run(
                    ["powershell", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=project_root
                )
        else:
            # Linux/Mac - use shell=True
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=project_root
            )
        
        output = result.stdout
        if result.stderr:
            output += f"\nError:\n{result.stderr}"
        return output
    except Exception as e:
        return f"Failed to execute command: {str(e)}"

def get_system_info() -> str:
    """
    Returns information about the system, including available browsers and display resolution.
    Use this to 'explore' the system before making assumptions about available software.
    """
    import platform
    import os
    
    info = []
    info.append("## System Information")
    info.append(f"- **Operating System**: {platform.system()} {platform.release()}")
    
    # Check for common browsers on Windows
    if platform.system() == "Windows":
        browsers = []
        paths = {
            "Chrome": [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
            ],
            "Edge": [
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")
            ],
            "Firefox": [
                os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe")
            ],
            "Brave": [
                os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe")
            ]
        }
        
        for name, possible_paths in paths.items():
            found = False
            for path in possible_paths:
                if os.path.exists(path):
                    browsers.append(f"  - **{name}**: `{path}`")
                    found = True
                    break
        
        if browsers:
            info.append("- **Available Browsers**:\n" + "\n".join(browsers))
        else:
            info.append("- **Available Browsers**: No common browsers detected via standard paths.")
            
        # Try to get screen resolution
        try:
            import pyautogui
            width, height = pyautogui.size()
            info.append(f"- **Screen Resolution**: {width}x{height}")
        except:
            pass
    elif platform.system() == "Linux":
        # Basic Linux discovery could go here, but focusing on user's Windows environment for now
        info.append("- Browser discovery for Linux not fully implemented, use `execute_command` with `which` or `ls` to find software.")
    
    return "\n".join(info)
