from http import client
import json
from datetime import date, timedelta
import mcp
import networkx as nx
import asyncio

from agents.mcp_agent import MCPAgent
from core.config import *
from core.constants import *
from core.graphql import *

import logging

# Silence the MCP and DataHub loggers
logging.getLogger("mcp_server_datahub").setLevel(logging.WARNING)
logging.getLogger("mcp.server.lowlevel.server").setLevel(logging.WARNING)


def build_lineage_graph(client):
    mcp = MCPAgent()

    result = asyncio.run(mcp.search("*"))

    G = nx.DiGraph()
    for res in result["searchResults"]:
        entity = res["entity"]
        urn = entity["urn"]

        if "nyc_taxi_pipeline" not in urn and "dashboard" not in urn:
            continue

        full_name = entity.get("properties", {}).get(
            "name", urn.split(",")[-1].replace(")", "")
        )

        name = full_name.split(".")[-1]
        asset_type = "DASHBOARD" if "dashboard" in urn else "DATASET"
        G.add_node(urn, name=name, type=asset_type)

    for urn in G.nodes:
        downstreams = client.lineage.get_lineage(
            source_urn=urn,
            direction="downstream",
        )

        for node in downstreams:
            if node.urn in G.nodes:
                G.add_edge(urn, node.urn)
    return G


def find_root_cause(G, stale_table_name):
    broken_table_urn = next(
        u for u in G.nodes if G.nodes[u]["name"] == stale_table_name
    )

    upstreams = [G.nodes[u]["name"] for u in G.predecessors(broken_table_urn)]

    if not upstreams:
        raise ValueError("Stale table has no upstream parent in DataHub lineage!")

    root_cause_source = upstreams[0]

    return broken_table_urn, stale_table_name, root_cause_source


def get_blast_radius(G, broken_table_urn):
    affected_nodes = []

    def traverse_downstream(node_urn):
        for child_urn in G.successors(node_urn):
            child_name = G.nodes[child_urn]["name"]
            child_type = G.nodes[child_urn]["type"]

            if child_name.startswith("v_"):
                traverse_downstream(child_urn)
                continue

            if child_urn not in affected_nodes:
                affected_nodes.append(
                    {"urn": child_urn, "name": child_name, "type": child_type}
                )
                traverse_downstream(child_urn)

    traverse_downstream(broken_table_urn)
    return affected_nodes


def build_llm_context(client, G, breach_result, broken_table_urn, upstream_source_urn):
    broken_node = G.nodes[broken_table_urn]
    upstream_node = G.nodes[upstream_source_urn]

    # Fetch descriptions dynamically from DataHub
    source_entity = client.entities.get(upstream_source_urn)

    target_entity = client.entities.get(broken_table_urn)

    source_schema_lines = []

    for field in source_entity.schema:
        source_schema_lines.append(
            f"{field.field_path} ({field.native_type}) - {field.description or 'No description'}"
        )

    source_schema = "\n".join(source_schema_lines)

    schema = []

    for field in target_entity.schema:
        schema.append(
            {
                "name": field.field_path,
                "type": field.native_type,
                "description": field.description or "",
            }
        )

    target_schema = json.dumps(schema, indent=2)

    # Safe description extraction with fallback
    source_desc = (
        getattr(source_entity, "description", None)
        or "Raw source dataset containing records."
    )
    target_desc = getattr(target_entity, "description", None) or "Target dataset."

    # Off-by-one correction
    backfill_start_date = date.fromisoformat(breach_result["stale_latest"]) + timedelta(
        days=1
    )

    return {
        "database_path": str(DATABASE_PATH),
        "source_table": upstream_node["name"],
        "target_table": broken_node["name"],
        "source_description": source_desc,
        "target_description": target_desc,
        "source_schema": source_schema,
        "target_schema": target_schema,
        "last_good_date": breach_result["stale_latest"],
        "latest_source_date": breach_result["raw_latest"],
        "backfill_start_date": backfill_start_date.isoformat(),
        "backfill_end_date": breach_result["raw_latest"],
        "gap_days": breach_result["gap_days"],
        "timestamp_column": target_entity.custom_properties["timestamp_column"],
        "transformation_logic": target_entity.custom_properties["transformation_logic"],
    }
