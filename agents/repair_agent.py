import json
import os
import shutil
from core.context_kit import build_agent_context
import asyncio
from agents.mcp_agent import MCPAgent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from rich.console import Console
from agents.investigator_agent import (
    build_llm_context,
    find_root_cause,
    get_blast_radius,
)
from core.config import *
from core.constants import *
from core.graphql import *
from core.prompts import *
from core.llm_cache import llm_call
from core.safety import (
    safety_validate_generated_script,
    validate_generated_script,
    validate_generated_sql,
)

console = Console()
from core.prompts import REPAIR_RETRY_PROMPT

llm = None


def regenerate_after_failure(
    llm,
    previous_script,
    error_message,
    context,
):
    prompt = f"""
You previously generated the following repair script.
== PREVIOUS SCRIPT ==
{previous_script}
The script failed because:
{error_message}
You MUST fix ONLY the cause of the failure.
Do NOT rewrite the whole repair.
Dataset information:
Source table:
{context["source_table"]}
Target table:
{context["target_table"]}
Timestamp column:
{context["timestamp_column"]}
Transformation logic:
{context["transformation_logic"]}
Source schema:
{context["source_schema"]}
Target schema:
{context["target_schema"]}
Agent Context
{context["agent_context"]}
Rules
- Return ONLY Python.
- No markdown.
- No explanation.
- Only modify what is necessary.
- Only touch the source and target datasets.
"""
    messages = [
        SystemMessage(content="You are an expert ETL repair engineer."),
        HumanMessage(content=prompt),
    ]

    cache_key = f"retry_repair:{context['target_table']}"
    corrected_script = llm_call(llm, messages, cache_key=cache_key)
    if corrected_script.startswith("```"):
        lines = corrected_script.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        corrected_script = "\n".join(lines)
    return corrected_script


def generate_repair(client, G, breach_result):
    stale_table_name = breach_result["stale_table"]
    broken_table_urn, broken_table_name, upstream_source_name = find_root_cause(
        G,
        stale_table_name,
    )
    upstream_source_urn = next(u for u in G.predecessors(broken_table_urn))
    blast_radius = get_blast_radius(G, broken_table_urn)
    with open(
        f"examples/blast_radius_{broken_table_name}.json", "w", encoding="utf-8"
    ) as f:
        json.dump(blast_radius, f, indent=4)
    blast_radius_names = [node["name"] for node in blast_radius]
    console.print(
        f"[bold yellow]ROOT CAUSE:[/] {broken_table_name} is stale (depends on {upstream_source_name})."
    )
    console.print(f"[bold magenta]BLAST RADIUS:[/] {blast_radius_names}")

    console.print("\n[bold cyan]FIXING:[/] Preparing LLM prompt...")
    context = build_llm_context(
        client, G, breach_result, broken_table_urn, upstream_source_urn
    )
    console.print("[bold cyan]MCP:[/] Retrieving live DataHub metadata...")
    mcp = MCPAgent()
    mcp_context = asyncio.run(
        mcp.build_mcp_context(
            broken_table_urn,
        )
    )
    context["mcp_entity"] = json.dumps(
        mcp_context["entity"],
        separators=(",", ":"),
    )
    context["mcp_schema"] = json.dumps(
        mcp_context["schema"][:15],
        separators=(",", ":"),
    )
    context["mcp_queries"] = json.dumps(
        mcp_context["queries"][:2],
        separators=(",", ":"),
    )
    agent_context = build_agent_context(context)
    context["agent_context"] = json.dumps(
        agent_context,
        indent=2,
    )
    console.print("[green]OK[/] Entity metadata")
    console.print("[green]OK[/] Schema")
    console.print("[green]OK[/] Dataset queries")
    prompt = PROMPT_TEMPLATE.format(**context)
    os.makedirs("examples", exist_ok=True)
    with open(f"examples/prompt_{broken_table_name}.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    messages = [
        SystemMessage(
            content="You are a senior Python Data Engineer who writes production-quality ETL repair scripts."
        ),
        HumanMessage(content=prompt),
    ]
    cache_key = f"generate_repair:{broken_table_name}"

    if DEMO_MODE:
        llm = None
        console.print(
            f"[bold cyan]JUDGE MODE:[/] Replaying cached repair script for {broken_table_name}..."
        )
        backfill_script = llm_call(llm, messages, cache_key=cache_key)
    else:
        if not GROQ_API_KEY:
            console.print(
                "[bold red]ERROR:[/] GROQ_API_KEY environment variable not set. Exiting."
            )
            return
        llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model="openai/gpt-oss-120b",
            temperature=0,
            max_tokens=4096,
        )
        console.print(
            "[bold cyan]CALLING:[/] Requesting backfill script from Groq LLM..."
        )
        backfill_script = None
        for attempt in range(MAX_LLM_RETRIES):
            try:
                backfill_script = llm_call(llm, messages, cache_key=cache_key)
                break
            except Exception as e:
                console.print(f"[yellow]LLM attempt {attempt + 1} failed:[/] {e}")
                if attempt == MAX_LLM_RETRIES - 1:
                    console.print("[bold red]All retries failed.[/]")
                    return

    if backfill_script.startswith("```"):
        lines = backfill_script.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        backfill_script = "\n".join(lines)

    # Save generated repair script
    filename = OUTPUT_DIR / (f"generated_backfill_{broken_table_name}.py")
    for repair_attempt in range(MAX_REPAIR_ATTEMPTS):
        filename.write_text(
            backfill_script,
            encoding="utf-8",
        )
        try:
            validate_generated_script(filename)
            safety_validate_generated_script(filename)
            validate_generated_sql(
                filename,
                context["source_table"],
                context["target_table"],
            )
            break
        except Exception as e:
            console.print(f"[yellow]Repair rejected:[/] {e}")
            console.print("[cyan]Repair Critic Agent fixing script...[/]")
            backfill_script = regenerate_after_failure(
                llm=llm,
                previous_script=backfill_script,
                error_message=str(e),
                context=context,
            )
    else:
        raise RuntimeError("Unable to generate a safe repair after multiple attempts.")
    os.makedirs("examples", exist_ok=True)
    shutil.copy(
        filename,
        EXAMPLES_DIR / filename.name,
    )
    console.print(
        f"[bold green]SUCCESS:[/] Backfill script generated and saved as {filename}"
    )
    return {
        "script_path": filename,
        "context": context,
        "mcp_context": mcp_context,
        "broken_table_urn": broken_table_urn,
        "broken_table_name": broken_table_name,
        "upstream_source_name": upstream_source_name,
        "upstream_source_urn": upstream_source_urn,
        "blast_radius": blast_radius,
        "blast_radius_names": blast_radius_names,
        "llm": llm,
    }
