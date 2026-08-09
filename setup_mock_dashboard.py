# RUN THIS ONCE BEFORE YOUR DEMO
from datahub.sdk.main_client import DataHubClient
from datahub.sdk import Dashboard
from datahub_agent_context.langchain_tools import build_langchain_tools
from rich.console import Console

console = Console()


def setup():
    client = DataHubClient.from_env()

    # Use the LangChain tool wrapper
    tools = build_langchain_tools(client, include_mutations=False)
    tool_map = {tool.name: tool for tool in tools}
    search_tool = tool_map["search"]

    # Explicitly search for mart_daily_summary
    console.print("[bold cyan]SEARCHING:[/] Looking for mart_daily_summary...")
    result = search_tool.invoke(
        {"query": "mart_daily_summary", "filter": "type = 'DATASET'"}
    )

    if not result.get("searchResults"):
        console.print("[bold red]ERROR:[/] Could not find mart_daily_summary.")
        return

    # Extract the URN from the first search result
    mart_urn = next(
        r["entity"]["urn"]
        for r in result["searchResults"]
        if "nyc_taxi_pipeline" in r["entity"]["urn"]
    )
    console.print(f"[bold green]FOUND:[/] {mart_urn}")

    # Create the CFO Dashboard
    cfo_dashboard = Dashboard(
        platform="superset",
        name="cfo_revenue_dashboard",
        display_name="CFO Revenue Dashboard",
        description="Executive overview of daily business revenue metrics.",
    )

    # Fetch the dataset object
    target_dataset = client.entities.get(mart_urn)

    # Link dashboard explicitly to mart_daily_summary
    cfo_dashboard.add_input_dataset(target_dataset)

    # Upsert to DataHub
    client.entities.upsert(cfo_dashboard)
    console.print(
        "[bold green]SUCCESS:[/] Published CFO Revenue Dashboard to DataHub database!"
    )


if __name__ == "__main__":
    setup()
