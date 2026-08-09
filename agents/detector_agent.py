from core.config import *
from datahub_agent_context.langchain_tools import build_langchain_tools
import sqlite3
from rich.console import Console
from datetime import datetime, date, timedelta
from agents.investigator_agent import build_lineage_graph
from datahub.sdk.main_client import DataHubClient

console = Console()


def confirm_freshness_breach(db_path=DATABASE_PATH):

    client = DataHubClient.from_env()

    tools = build_langchain_tools(client, include_mutations=False)
    tool_map = {tool.name: tool for tool in tools}
    search_tool = tool_map["search"]

    result = search_tool.invoke(
        {
            "query": "*",
            "filter": "type IN ('DATASET')",
        }
    )

    conn = sqlite3.connect(db_path)

    raw_table = None
    raw_timestamp = None

    datasets = []

    for res in result["searchResults"]:
        urn = res["entity"]["urn"]

        if "nyc_taxi_pipeline" not in urn:
            continue

        entity = client.entities.get(urn)

        props = entity.custom_properties or {}

        if props.get("is_view") == "True" or props.get("dataset_role") == "view":
            continue

        role = props.get("dataset_role")
        timestamp_column = props.get("timestamp_column")
        table_name = entity.urn.name.split(".")[-1]

        if not role or not timestamp_column:
            console.print(
                f"[yellow]Skipping dataset without required AI metadata:[/] {table_name}"
            )
            continue

        sla_days = int(props.get("sla_days", 1))

        if role == "source":
            raw_table = table_name
            raw_timestamp = timestamp_column
        else:
            datasets.append(
                {
                    "table": table_name,
                    "timestamp": timestamp_column,
                    "sla": sla_days,
                }
            )

    raw_latest = conn.execute(
        f"SELECT DATE(MAX({raw_timestamp})) FROM {raw_table}"
    ).fetchone()[0]

    stale_datasets = []

    for dataset in datasets:
        table = dataset["table"]
        timestamp = dataset["timestamp"]
        sla = dataset["sla"]

        latest = conn.execute(f"SELECT DATE(MAX({timestamp})) FROM {table}").fetchone()[
            0
        ]

        if latest is None:
            continue

        delta = (
            datetime.strptime(raw_latest, "%Y-%m-%d")
            - datetime.strptime(latest, "%Y-%m-%d")
        ).days

        console.print(f"{table:<25} latest={latest} gap={delta}")

        if delta > sla:
            stale_datasets.append(
                {
                    "table": table,
                    "gap_days": delta,
                    "raw_latest": raw_latest,
                    "stale_latest": latest,
                }
            )

    conn.close()

    if not stale_datasets:
        console.print("[bold green]OK:[/] Freshness SLA met.")
        return {"incident": False}

    G = build_lineage_graph(client)

    stale_names = {d["table"] for d in stale_datasets}

    for dataset in stale_datasets:
        urn = next(u for u in G.nodes if G.nodes[u]["name"] == dataset["table"])

        parents = [
            G.nodes[p]["name"]
            for p in G.predecessors(urn)
            if G.nodes[p]["type"] == "DATASET"
        ]

        stale_parent_exists = any(parent in stale_names for parent in parents)

        if not stale_parent_exists:
            console.print(
                f"[bold red]INCIDENT:[/]\n"
                f"Freshness SLA Breached!\n\n"
                f"Raw Latest      : {dataset['raw_latest']}\n"
                f"{dataset['table']} Latest : {dataset['stale_latest']}\n"
                f"Gap             : {dataset['gap_days']} day(s)"
            )

            return {
                "incident": True,
                "stale_table": dataset["table"],
                "gap_days": dataset["gap_days"],
                "raw_latest": dataset["raw_latest"],
                "stale_latest": dataset["stale_latest"],
            }

    return {
        "incident": True,
        **stale_datasets[0],
    }
