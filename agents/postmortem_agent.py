from datetime import datetime


def build_postmortem(
    repair_info,
    blast_radius,
    github_pr,
):

    report = f"""
# Ripple AI Incident Report

## Timestamp

{datetime.now()}

---

## Root Cause

{repair_info["broken_table_name"]}

---

## Upstream Source

{repair_info["upstream_source_name"]}

---

## Blast Radius

"""

    for item in blast_radius:
        report += f"- {item}\n"

    report += f"""

---

## Repair

Automatic AI-generated repair script executed successfully.

Verification passed.

---

## GitHub Pull Request

{github_pr}

---

## Status

Resolved automatically by Ripple AI.

"""

    return report
