# Ripple AI: Autonomous Self-Healing Data Pipelines

The first multi-agent system that uses DataHub's context graph as its working memory to safely execute physical pipeline repairs.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![DataHub](https://img.shields.io/badge/DataHub-MCP-orange.svg)
![LLM](https://img.shields.io/badge/LLM-Groq-green.svg)
![License](https://img.shields.io/badge/License-Apache%202.0-purple.svg)


Standard self-healing tools operate blindly on isolated logs. **Ripple AI** is a graph-native multi-agent framework that turns DataHub’s metadata catalog (via MCP) into an active working memory. Instead of just generating code snippets, Ripple AI uses the enterprise lineage graph to reason about root causes and safely execute physical database repairs in real time.

---

## The Problem

Data pipelines break silently, causing downstream data corruption across executive dashboards and ML models. Traditional tools lack situational awareness—they can't see the broader data topology. As a result, engineers spend hours manually mapping lineage graphs, assessing blast radius, writing backfills, and updating governance tags. AI couldn't safely resolve this until now because it lacked an active memory of the enterprise data stack. 

## The Solution: Ripple AI

Ripple AI operates as an autonomous Data Engineering team. When a freshness SLA is breached, Ripple AI:
1. **Detects** the anomaly automatically.
2. **Traces** the root cause and blast radius using DataHub lineage graphs.
3. **Warns** downstream users by automatically applying a `Stale Data - Do Not Use` glossary term to affected assets.
4. **Repairs** the pipeline by generating, validating, and executing a Python backfill script via Groq LLMs.
5. **Resolves** the incident by creating a GitHub Pull Request with the fix and logging a postmortem report back into DataHub.

## 🎥 Demo Video

<p align="center">
  <a href="https://youtu.be/g1XKOGHA2ac">
    <img src="https://img.youtube.com/vi/g1XKOGHA2ac/maxresdefault.jpg" alt="Ripple AI Demo" width="800">
  </a>
</p>

<p align="center">
  <b>▶ Watch Ripple AI detect, diagnose, and automatically fix a data pipeline failure.</b>
</p>


---

## Architecture & Agentic Workflow

Ripple AI is powered by a decentralized architecture of specialized agents:

*   **Coordinator Agent:** Orchestrates the entire lifecycle from detection to postmortem.
*   **Detector Agent:** Polls DataHub properties and database states to confirm Freshness SLA breaches.
*   **Investigator Agent:** Uses `NetworkX` to build a localized lineage graph, isolating the root cause and downstream blast radius.
*   **Repair & Critic Agents:** Prompts a `gpt-oss-120b` Groq model to generate a Python ETL script. Includes a critic-loop that validates Python AST safety (blocking destructive SQL or unauthorized imports) and regenerates code upon failure.
*   **Governance Agent:** Manages the DataHub state by raising Incidents, updating Assertions, and toggling Glossary terms.
*   **GitHub Agent:** Pushes the verified repair scripts to a new branch and automatically creates a Pull Request for human review.
*   **Knowledge Agent:** Saves incident postmortems back into DataHub for future LLM RAG context.

---

<img width="5371" height="3485" alt="hackahton" src="https://github.com/user-attachments/assets/59dbbfef-8b98-40a7-92a4-59aa08540392" />


## Tech Stack

*   **Core:** Python
*   **Metadata & Governance:** DataHub, Model Context Protocol (MCP), GraphQL
*   **LLM Provider:** Groq (`gpt-oss-120b`), LangChain
*   **Graph Processing:** NetworkX
*   **Database:** SQLite (Demo environment for NYC Taxi dataset)

---

## Getting Started

### Prerequisites
* Python 3.11 or 3.12 (3.13+ not supported — numpy/spaCy-related build tooling issues)
* A running instance of DataHub (`localhost:8080`)
* Groq API Key( For live call)
* GitHub Personal Access Token (for PR creation) [For live call]

### 1. Installation

Clone the repository and install dependencies:
```bash
git clone https://github.com/R0GUE-A5H/ripple-ai.git
cd ripple-ai
pip install -r requirements.txt
```

### 2. Configuration (DEMO MODE)
Create a `.env` file in the root directory and configure the following variables:
```
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token
GITHUB_OWNER=your_github_username
GITHUB_REPO=your_github_repo  # assuming your forking it
GMS_URL=http://localhost:8080/api/graphql
DATAHUB_GMS_URL=http://localhost:8080
LOCAL_REPO=.
DEMO_MODE=false
RECORD_CACHE=false
LOG_LEVEL=INFO
```
On how to generate GITHUB_TOKEN (PAT GRAINED) [Click Here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)
> 💡 **NOTE FOR JUDGES**: You can run this project without creating a `.env` file. Ripple AI includes a **Judge/Demo** Mode that safely simulates LLM responses and GitHub PR creations without requiring live API keys. You can run it **as-is** immediately after cloning.

### 3. HOW TO RUN
After cloning, you can either create a .env file or run the project immediately. Running it without a .env file triggers Demo Mode, which uses pre-generated artifacts from a live call. Before running, ensure you have removed previous datasets or ingested metadata. Alternatively, you can run `datahub docker nuke` to ensure a completely clean state.

```bash
datahub docker quickstart
cd ripple-ai/nyc-taxi
datahub ingest -c ingest_pipeline.yaml
python add_metadata.py --instance=nyc_taxi_pipeline
python add_lineage.py --instance=nyc_taxi_pipeline
cd ripple-ai
python -u setup.py
```
**Note:** You must run `setup.py` at the root folder to kick off the pipeline process.

### 4. What to Expect

When running the process, look for the following steps in the console:

* **Contextual Anomaly Detection:** Reads DataHub assertion states to identify that `staging_trips` is 9 days stale.
* **Graph Blast Radius Analysis:** Queries DataHub’s lineage graph via MCP to isolate downstream impact (`mart_daily_summary`, `CFO Revenue Dashboard`) and automatically applies `Stale Data` glossary tags to protect consumers.
* **Safe Physical Remediation:** Prompts the LLM for backfill code, verifies script safety through an AST static-analysis sandbox, and executes the physical database repair with auto-rollback protection.
* **Governance & Resolution:** Creates a GitHub PR with the fix, writes a permanent postmortem back into DataHub's context graph, and marks the incident resolved.

### 5. Safety & Guardrails
*   **Code Sandboxing:** Ripple AI does not blindly run LLM-generated code.
*   **AST Validation:** Utilizes strict Abstract Syntax Tree (AST) scanning to prevent the usage of `exec`, `eval`, `subprocess`, and destructive SQL statements like `DROP TABLE`.
*   **Snapshot Rollbacks:** Creates a temporary database snapshot before executing repairs, rolling back automatically if the generated ETL script encounters an error.
*   **Human-in-the-Loop:** Requires explicit human approval (`Y/N/O`) before executing a generated script in live environments.
