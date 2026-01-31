import subprocess
import platform

def execute_command(command: str) -> str:
    """
    Executes a shell command on the local system.
    
    Args:
        command: The command to execute.
        
    Returns:
        The output of the command or error message.
    """
    try:
        # Use shell=True to allow complex commands. 
        # CAUTION: This allows arbitrary code execution.
        system = platform.system()
        project_root = r"d:\openclaw_lite"
        if system == "Windows":
             result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, timeout=60, cwd=project_root)
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60, cwd=project_root)
        
        output = result.stdout
        if result.stderr:
            output += f"\nError:\n{result.stderr}"
        return output
    except Exception as e:
        return f"Failed to execute command: {str(e)}"
