from rich.console import Console

console = Console()


class KnowledgeAgent:
    def __init__(self, mcp):

        self.mcp = mcp

    async def search_previous_incidents(
        self,
        table_name,
    ):

        console.print(
            "[bold cyan]KNOWLEDGE AGENT:[/] Searching previous Ripple incidents..."
        )

        result = await self.mcp.search(f"Ripple Incident {table_name}")

        return result

    def summarize(
        self,
        search_result,
    ):

        try:
            results = search_result.structuredContent["searchResults"]

        except Exception:
            return ""

        if not results:
            console.print("[yellow]No previous Ripple incidents found.[/]")

            return ""

        summary = []

        for item in results[:3]:
            entity = item.get("entity", {})

            name = entity.get("properties", {}).get("name", "")

            if name:
                summary.append(name)

        console.print(f"[green]Found {len(summary)} previous knowledge document(s).[/]")

        return "\n".join(summary)
