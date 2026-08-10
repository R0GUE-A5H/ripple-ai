# examples/

Real generated output from a single run of Ripple AI against DataHub's
`nyc_taxi_pipeline` sample dataset — not fixtures, not illustrations. This
folder exists so a judge can evaluate the project's output without running
any code or standing up a DataHub instance, per the hackathon's submission
guidance.

## Contents

| File | What it shows |
|---|---|
| `run_summary.txt` | Full terminal log: detection, root-cause trace, blast radius, fix generation, execution, verification, PR creation, write-back. |
| `lineage_graph.gml` | Dependency graph retrieved from DataHub via the Agent Context Kit. Load with `networkx.read_gml()`. |
| `context_staging_trips.json` | Structured incident context for the `staging_trips` fix: gap in days, missing date range, table schema, transformation rules. |
| `context_mart_daily_summary.json` | Same, for `mart_daily_summary`. |
| `mcp_context_staging_trips.json` | Raw context retrieved from DataHub's MCP Server for the `staging_trips` incident. |
| `prompt_staging_trips.txt` | Prompt sent to the LLM to generate the `staging_trips` fix. |
| `prompt_mart_daily_summary.txt` | Prompt sent to the LLM to generate the `mart_daily_summary` fix. |
| `generated_backfill_staging_trips.py` | LLM-generated fix, row-level backfill from `raw_trips` into `staging_trips`. |
| `generated_backfill_mart_daily_summary.py` | LLM-generated fix, aggregate backfill from `staging_trips` into `mart_daily_summary`. |
| `blast_radius_staging_trips.json` | Downstream assets affected by the `staging_trips` break, from a recursive lineage walk. |
| `blast_radius_mart_daily_summary.json` | Same, for `mart_daily_summary`. |
| `notification_message.md` | Generated incident summary. |
| `incident_postmortem.md` | Final incident report, generated after both incidents were verified resolved. Also written back into DataHub as a Document. |

## What's real vs. generated

- `context_*.json` and `blast_radius_*.json` are computed entirely by SQL
  queries and lineage graph traversal against DataHub — no LLM involvement.
- `generated_backfill_*.py` is LLM output, constrained to the facts in the
  matching `context_*.json` and `prompt_*.txt`. Each script went through AST
  validation and required human approval before it was executed (see root
  `README.md`).
  
## Regenerate

```bash
python -u setup.py
```

Runs the full pipeline against a fresh `nyc_taxi_pipeline` ingest and
overwrites this folder with a new run's output.
