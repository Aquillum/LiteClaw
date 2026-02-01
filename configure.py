import subprocess
import sys
import os

def main():
    # Detect the correct command to run
    # If in dev environment, we might need to run python -m liteclaw.cli 
    # But usually .venv/Scripts/liteclaw is available.
    
    cmd = ["liteclaw", "configure"]
    
    # Try to find the local execution command if 'liteclaw' isn't in PATH
    if os.name == 'nt':
        venv_bin = os.path.join(".venv", "Scripts", "liteclaw.exe")
        if os.path.exists(venv_bin):
            cmd = [venv_bin, "configure"]
    else:
        venv_bin = os.path.join(".venv", "bin", "liteclaw")
        if os.path.exists(venv_bin):
            cmd = [venv_bin, "configure"]

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        # Fallback to python -m
        subprocess.run([sys.executable, "-m", "liteclaw.cli", "configure"])

if __name__ == "__main__":
    main()
