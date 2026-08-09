from rich.console import Console
from agents.detector_agent import confirm_freshness_breach

console = Console()


def verify_repair():
    console.print("[cyan]VERIFYING:[/] Rechecking freshness...")

    verification = confirm_freshness_breach()

    if verification["incident"]:
        console.print(
            f"[bold yellow]NEXT INCIDENT DETECTED:[/] "
            f"{verification['stale_table']} is still stale "
            f"({verification['gap_days']} day(s))."
        )

        return verification

    console.print("[bold green]VERIFIED:[/] Freshness SLA is now satisfied.")

    return None
