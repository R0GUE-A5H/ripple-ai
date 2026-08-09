import json
import logging
import os
import subprocess
import json
from core.approval import request_human_approval
from agents.postmortem_agent import build_postmortem

import networkx as nx
from datahub.sdk.main_client import DataHubClient
from rich.console import Console
from agents.detector_agent import confirm_freshness_breach
from agents.governance_agent import *
from agents.investigator_agent import *
from agents.repair_agent import *
from core.safety import apply_generated_repair, validate_generated_script
from agents.verifier_agent import verify_repair
from agents.github_agent import *
from core.postmortem import *
from agents.mcp_agent import *

console = Console()


def main():
    os.makedirs("examples", exist_ok=True)

    logging.basicConfig(
        filename="examples/sample_run.log",
        level=logging.INFO,
        format="%(asctime)s %(message)s",
    )
    console.print("[bold cyan]RUNNING:[/] Freshness check on nyc_taxi_pipeline\n")
    breach_result = confirm_freshness_breach()
    logging.info("Freshness breach detected")

    if not breach_result["incident"]:
        console.print("[bold green]OK:[/] Freshness SLA met. Exiting.")
        return

    stale_table_name = breach_result["stale_table"]
    console.print(
        f"[bold red]INCIDENT:[/] {stale_table_name} is {breach_result['gap_days']} days stale!"
    )

    console.print("\n[bold cyan]INVESTIGATING:[/] Building DataHub context graph...")
    client = DataHubClient.from_env()
    mcp = MCPAgent()
    G = build_lineage_graph(client)
    nx.write_gml(G, "examples/lineage_graph.gml")

    broken_table_urn, broken_table_name, upstream_source_name = find_root_cause(
        G,
        breach_result["stale_table"],
    )

    upstream_source_urn = next(u for u in G.predecessors(broken_table_urn))

    blast_radius = get_blast_radius(
        G,
        broken_table_urn,
    )

    blast_radius_names = [node["name"] for node in blast_radius]

    context = build_llm_context(
        client,
        G,
        breach_result,
        broken_table_urn,
        upstream_source_urn,
    )

    all_blast_radius = {}
    generated_scripts = []
    pr_url = None

    term_urn = ensure_warning_glossary_term()

    all_incidents = []
    all_assertions = []

    while breach_result["incident"]:
        repair_info = generate_repair(
            client,
            G,
            breach_result,
        )
        if repair_info is None:
            return
        logging.info(
            "Repair generated for %s",
            repair_info["broken_table_name"],
        )

        script_path = repair_info["script_path"]
        generated_scripts.append(script_path)
        llm = repair_info["llm"]

        context = repair_info["context"]
        mcp_context = repair_info["mcp_context"]
        with open(
            f"examples/context_{repair_info['broken_table_name']}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(context, f, indent=4)

        with open(
            f"examples/mcp_context_{broken_table_name}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                mcp_context,
                f,
                indent=4,
            )

        broken_table_urn = repair_info["broken_table_urn"]
        broken_table_name = repair_info["broken_table_name"]

        upstream_source_name = repair_info["upstream_source_name"]
        upstream_source_urn = repair_info["upstream_source_urn"]

        blast_radius = repair_info["blast_radius"]
        for node in blast_radius:
            all_blast_radius[node["urn"]] = node
        blast_radius_names = repair_info["blast_radius_names"]

        assertion_urn = ensure_freshness_assertion(
            broken_table_urn,
            broken_table_name,
        )

        wait_and_report_assertion(
            assertion_urn,
            "FAILURE",
        )

        all_assertions.append(assertion_urn)

        incident_urn = raise_datahub_incident(
            broken_table_name,
            broken_table_urn,
            context,
        )

        all_incidents.append(incident_urn)

        add_glossary_terms(
            blast_radius,
            term_urn,
        )

        validate_generated_script(script_path)
        approved = request_human_approval(script_path)

        if not approved:
            raise RuntimeError("Repair aborted by operator.")
        for execution_attempt in range(MAX_REPAIR_ATTEMPTS):
            success, runtime_error = apply_generated_repair(script_path)

            if success:
                break

            console.print("[yellow]Repair execution failed.[/]")

            console.print("[cyan]Repair Critic Agent analyzing runtime failure...[/]")
            filename = OUTPUT_DIR / (f"generated_backfill_{broken_table_name}.py")
            previous_script = filename.read_text(
                encoding="utf-8",
            )

            corrected_script = regenerate_after_failure(
                llm=llm,
                previous_script=previous_script,
                error_message=runtime_error,
                context=context,
            )

            filename.write_text(corrected_script, encoding="utf-8")

            validate_generated_script(script_path)

            safety_validate_generated_script(script_path)

            validate_generated_sql(
                script_path,
                context["source_table"],
                context["target_table"],
            )

        else:
            raise RuntimeError("Repair failed after multiple execution attempts.")

        verification = verify_repair()
        if verification is not None:
            console.print(
                "[yellow]Repair not fully verified. Snapshot retained until all downstream datasets are repaired.[/]"
            )

        if verification is None:
            for urn in all_assertions:
                wait_and_report_assertion(
                    urn,
                    "SUCCESS",
                )
            logging.info("Repair verified")
            branch = None
            branch, filenames = push_repairs_to_github(generated_scripts)
            pr_url = create_pull_request(
                branch,
                broken_table_name,
                context["gap_days"],
                filenames,
            )
            dataset_names = [
                os.path.splitext(Path(script).name)[0].replace(
                    "generated_backfill_", ""
                )
                for script in generated_scripts
            ]

            generate_postmortem(
                dataset_names,
                all_blast_radius,
                pr_url,
            )
            if pr_url:
                if not DEMO_MODE:
                    subprocess.run(
                        ["git", "branch", "-D", branch],
                        cwd=str(LOCAL_REPO),
                        check=True,
                    )
            else:
                console.print(
                    "[yellow]PR creation failed. Keeping local branch for debugging.[/"
                )

            console.print("[bold green]Repair verified successfully.[/]")
            report = build_postmortem(
                repair_info,
                blast_radius_names,
                pr_url,
            )
            console.print()

            console.print("[bold cyan]POSTMORTEM AGENT[/]")

            console.print("Building incident report...")

            console.print("Writing knowledge back into DataHub...")

            result = asyncio.run(
                mcp.save_document(
                    document_type="Context",
                    title=f"Ripple Incident - {repair_info['broken_table_name']}",
                    content=report,
                    topics=[
                        "freshness",
                        "self-healing",
                        "data-quality",
                        "ripple-ai",
                    ],
                    related_assets=[
                        repair_info["broken_table_urn"],
                    ],
                )
            )
            console.print("[green]Knowledge stored in DataHub.[/]")
            break

        console.print(
            f"[bold yellow]Switching to next stale dataset:[/] "
            f"{verification['stale_table']}"
        )

        breach_result = verification
    console.print(
        "\n[bold green]SELF-HEAL COMPLETE:[/] All freshness violations resolved."
    )

    console.print("[bold cyan]CLEANUP:[/] Synchronizing DataHub catalog...")

    console.print(
        "\n[bold cyan]RIPPLING:[/] Writing blast radius and incidents back to DataHub..."
    )
    if DEMO_MODE:
        time.sleep(5)

    remove_glossary_terms(
        list(all_blast_radius.values()),
        term_urn,
    )

    for incident in all_incidents:
        resolve_datahub_incident(incident)

    datasets = [n for n in blast_radius if n["type"] == "DATASET"]

    dashboards = [n for n in blast_radius if n["type"] == "DASHBOARD"]

    dataset_list = ", ".join(n["name"] for n in datasets) or "None"

    dashboard_list = ", ".join(n["name"] for n in dashboards) or "None"

    slack_message = f"""
    DATAHUB RIPPLE AGENT ALERT

    Incident
    --------
    Freshness SLA Breach on `{broken_table_name}`

    Root Cause
    ----------
    {context["gap_days"]} day(s) behind upstream source `{upstream_source_name}`

    Affected Datasets
    -----------------
    {dataset_list}

    Affected Dashboards
    -------------------
    {dashboard_list}

    Repair Status
    -------------
    Repair completed successfully.
    Freshness SLA verified.

    Pull Request
    ------------
    {pr_url}

    Governance
    ----------
    Glossary term applied during remediation and removed after successful verification.
    """

    os.makedirs("examples", exist_ok=True)
    with open("examples/notification_message.md", "w", encoding="utf-8") as f:
        f.write(slack_message.strip())

    console.print(
        "\n[bold green]SUCCESS:[/] Agent run complete. Catalog updated. Business protected."
    )
    console.print()

    console.print("[bold cyan]---- RIPPLE AI SUMMARY ----[/]")

    console.print(f"Datasets repaired      : {len(generated_scripts)}")

    console.print(f"Repair scripts created : {len(generated_scripts)}")

    console.print(f"Blast radius size      : {len(all_blast_radius)}")

    console.print(f"GitHub PR              : {pr_url}")

    console.print(f"Incident resolved      : Yes")

    console.print(f"Assertions updated     : Yes")

    console.print(f"Governance restored    : Yes")

    dataset_names = [
        os.path.splitext(Path(script).name)[0].replace(
            "generated_backfill_",
            "",
        )
        for script in generated_scripts
    ]

    repair_names = [Path(script).name for script in generated_scripts]

    blast_names = [node["name"] for node in all_blast_radius.values()]

    summary = f"""Ripple AI Run Summary

    Datasets repaired:
    {chr(10).join("- " + d for d in dataset_names)}

    Repair scripts:
    {chr(10).join("- " + r for r in repair_names)}

    Blast Radius:
    {chr(10).join("- " + b for b in blast_names)}

    GitHub Pull Request:
    {pr_url}

    Incident:
    Resolved

    Assertions:
    Updated

    Governance:
    Restored
    """

    with open(
        "examples/run_summary.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(summary)
