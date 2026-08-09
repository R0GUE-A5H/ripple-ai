from rich.console import Console
import os
from core.config import DEMO_MODE

console = Console()


def request_human_approval(script_path):
    console.print()
    if DEMO_MODE:
        console.print(
            "[bold yellow]JUDGE MODE:[/] Auto-approving generated repair "
            "(no interactive prompt while DEMO_MODE=true)."
        )
        console.print(f"Review the generated repair script:\n\n{script_path}\n")
        return True

    console.print("[bold yellow]HUMAN APPROVAL REQUIRED[/]")
    console.print()
    console.print(f"Review the generated repair script:\n\n{script_path}\n")
    while True:
        answer = input("Execute repair? (Y/N/O): ").strip().lower()
        if answer == "y":
            console.print("[green]Repair approved.[/]")
            return True
        if answer == "n":
            console.print("[red]Repair cancelled by operator.[/]")
            return False
        if answer == "o":
            os.startfile(script_path)
            continue
        console.print("Please enter Y or N.")
