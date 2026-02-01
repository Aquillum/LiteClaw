import os
import sys
import subprocess
import glob
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def check_python_syntax():
    console.print("[bold blue]🔍 Checking Python Syntax...[/bold blue]")
    py_files = glob.glob("**/*.py", recursive=True)
    errors = False
    for file in py_files:
        if file.startswith("venv") or file.startswith(".venv") or "node_modules" in file:
            continue
        try:
            with open(file, "r", encoding="utf-8") as f:
                compile(f.read(), file, "exec")
        except SyntaxError as e:
            console.print(f"[red]❌ Syntax Error in {file}: {e}[/red]")
            errors = True
        except Exception as e:
            # Maybe encoding error or similar
            console.print(f"[yellow]⚠️ Could not check {file}: {e}[/yellow]")
    
    if not errors:
        console.print("[green]✅ Python Syntax OK[/green]")
    return not errors

def check_bridge_structure():
    console.print("\n[bold blue]🔍 Checking Node Bridge...[/bold blue]")
    bridge_path = Path("src/liteclaw/bridge")
    if not bridge_path.exists():
        console.print("[red]❌ Bridge directory missing![/red]")
        return False
    
    required = ["index.js", "package.json"]
    missing = [f for f in required if not (bridge_path / f).exists()]
    
    if missing:
        console.print(f"[red]❌ Missing bridge files: {', '.join(missing)}[/red]")
        return False
    
    console.print("[green]✅ Bridge Structure OK[/green]")
    return True

def run_import_test():
    console.print("\n[bold blue]🔍 Verifying Package Imports...[/bold blue]")
    try:
        # Try to import the main package
        subprocess.check_call([sys.executable, "-c", "import liteclaw; print('Import successful')"])
        console.print("[green]✅ Core Package Import OK[/green]")
        return True
    except subprocess.CalledProcessError:
        console.print("[red]❌ Failed to import 'liteclaw' package[/red]")
        return False

def main():
    console.print(Panel("[bold]LiteClaw PR Validation Script[/bold]"))
    
    root_dir = Path(__file__).parent.parent
    os.chdir(root_dir)
    
    passed = True
    passed &= check_python_syntax()
    passed &= check_bridge_structure()
    passed &= run_import_test()
    
    if passed:
        console.print("\n[bold green]🎉 All checks passed! Ready for PR.[/bold green]")
        sys.exit(0)
    else:
        console.print("\n[bold red]💥 Some checks failed. Please fix before pushing.[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
