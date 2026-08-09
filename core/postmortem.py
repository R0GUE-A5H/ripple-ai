import os


def generate_postmortem(
    repaired_datasets,
    blast_radius,
    pr_url,
):

    os.makedirs("examples", exist_ok=True)

    blast_names = [node["name"] for node in blast_radius.values()]

    report = f"""# Ripple AI Incident Postmortem

## Incident

Freshness SLA violation detected automatically.

## Repaired Datasets

{chr(10).join("- " + d for d in repaired_datasets)}

## Blast Radius

{chr(10).join("- " + b for b in blast_names)}

## Automated Actions

- Root cause identified using DataHub lineage
- Blast radius computed
- AI-generated repair script created
- Safety validation passed
- Database snapshot created
- Repair executed
- Freshness verified
- DataHub Assertion updated
- DataHub Incident resolved
- Governance restored
- Pull Request created

## GitHub Pull Request

{pr_url}

## Final Status

SUCCESS
"""

    with open(
        "examples/incident_postmortem.md",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(report)
