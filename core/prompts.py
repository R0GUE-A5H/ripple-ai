PROMPT_TEMPLATE = """
ROLE
You are a senior Python Data Engineer responsible for repairing failed ETL pipelines.
OBJECTIVE
An automated DataHub AI agent has detected a freshness SLA breach and already completed the root-cause analysis.
Your task is to generate a production-ready Python backfill script that repairs the broken dataset.
================
DISCOVERED FACTS (Authoritative - Use ONLY these facts)
================
Database
---------
Path:
{database_path}
Source Dataset
--------------
Name:
{source_table}
Description:
{source_description}
Target Dataset
--------------
Name:
{target_table}
Description:
{target_description}
Freshness Analysis
------------------
Last successfully processed date:
{last_good_date}
Latest available source date:
{latest_source_date}
Missing date range (inclusive):
{backfill_start_date}
through
{backfill_end_date}
Gap:
{gap_days} days

================
SOURCE SCHEMA
==================
{source_schema}
================
TARGET SCHEMA
=================
{target_schema}
====================
TRANSFORMATION LOGIC
=====================
The target dataset is produced using the following business rules.

{transformation_logic}

------
DATAHUB AGENT CONTEXT
------
The following structured context has already been
assembled by the Ripple AI Agent Context Kit.
Use it as the authoritative summary.

{agent_context}

----------
Instructions
- Use this metadata for additional grounding.
- If the schema retrieved through MCP contains extra details,
  prefer it over assumptions.
- Use previous dataset queries to better understand how this
  dataset is consumed.
- Never invent metadata that is not present in the MCP context.
=================
IMPLEMENTATION REQUIREMENTS
=================
1. Use ONLY Python's built-in sqlite3 module for database operations.

2. Allowed standard library imports are limited to:
   - sqlite3
   - logging
   - datetime
   - time
   - os
   - sys
   - pathlib
   - contextlib
   - typing
   - collections
   - itertools

3. Do NOT import any third-party libraries.
4. Connect to the SQLite database located at:
{database_path}

5. Start a database transaction using BEGIN.
6. Delete ONLY rows from "{target_table}" whose {timestamp_column} falls inside the missing date range.
7. Recompute the missing data for "{target_table}" from "{source_table}" strictly according to the supplied Transformation Logic.
8. Insert the recomputed rows into "{target_table}".
9. The INSERT statement MUST explicitly specify the destination columns.
10. Use ONLY the columns listed in the Target Schema.
11. Never reference columns that are not present in the Target Schema.
12. Never invent:
    - columns
    - tables
    - SQL functions
    - business rules

13. Every SQL statement must be syntactically valid SQLite.
14. Use parameterized SQL placeholders (?) for every SQL parameter.
15. Commit the transaction only if every operation succeeds.
16. Roll back the transaction if any exception occurs.
17. Always close the database connection.
18. Use Python's logging module.
Log at least:

- Opening database
- Transaction started
- Rows deleted
- Rows inserted
- Commit successful
- Rollback (if needed)
- Database closed

19. Include
def main()
and
if __name__ == "__main__":
    main()
===============
RESTRICTIONS
===============
Do NOT invent:
- tables
- columns
- transformations
- business logic

Use ONLY:
- Database Path
- Source Dataset
- Target Dataset
- Target Schema
- Transformation Logic
- Freshness Analysis
If the Transformation Logic describes row-level processing, generate row-level SQL.
If the Transformation Logic describes aggregation, generate aggregation SQL.
Never assume aggregations unless explicitly specified by the Transformation Logic.
=======
OUTPUT
======
Return ONLY executable Python code.
Do NOT use Markdown.
Do NOT explain your reasoning.
Do NOT output any text besides the Python script.
"""

REPAIR_RETRY_PROMPT = """
The previous repair script failed validation or execution.
=======
PREVIOUS SCRIPT
======
{script}
=======
ERROR
========
{error}
========
TASK
=======
Fix ONLY the reported error.
Do NOT change:
- business logic
- transformation logic
- source table
- target table
- logging
- transactions
Preserve all working code.
Return the FULL corrected Python script.
Return ONLY executable Python code.
=================
PREVIOUS INCIDENT KNOWLEDGE
=================
{previous_repairs}
=================
If previous successful repairs exist, use them as guidance.
Do NOT copy them blindly.
Use them only when applicable.
==================
"""
