import requests
from core.config import *
from core.constants import *
from core.graphql import *


def raise_datahub_incident(broken_table_name, broken_table_urn, context):

    incident_mutation = """
    mutation raiseIncident($input: RaiseIncidentInput!) {
        raiseIncident(input: $input)
    }
    """

    incident_variables = {
        "input": {
            "type": "OPERATIONAL",
            "title": f"Freshness SLA Breach: {broken_table_name}",
            "description": (
                f"Dataset: {broken_table_name}\n"
                f"Freshness Gap: {context['gap_days']} day(s)\n"
                f"Latest Source Date: {context['latest_source_date']}\n"
                f"Last Processed Date: {context['last_good_date']}\n\n"
                "Ripple AI generated an automated repair script and "
                "started remediation."
            ),
            "resourceUrn": broken_table_urn,
        }
    }

    for attempt in range(3):
        try:
            response = requests.post(
                GMS_URL,
                json={
                    "query": incident_mutation,
                    "variables": incident_variables,
                },
                headers=headers,
            )

            result = response.json()

            if "errors" in result:
                console.print(
                    f"[bold red]GraphQL Incident Error:[/] {result['errors']}"
                )
                return None

            console.print("[bold green]UPSERTED:[/] Created Incident.")

            return result["data"]["raiseIncident"]

        except Exception as e:
            if attempt == 2:
                console.print(f"[bold red]Incident creation failed:[/] {e}")
                return None

            console.print(f"[yellow]Retrying GraphQL ({attempt + 1})[/]")


def ensure_warning_glossary_term():

    variables = {
        "input": {
            "id": "stale-data-do-not-use",
            "name": "Stale Data - Do Not Use",
            "description": "Automatically assigned by Ripple AI while downstream assets may contain stale data.",
        }
    }

    response = requests.post(
        GMS_URL,
        json={"query": CREATE_GLOSSARY_TERM, "variables": variables},
        headers=headers,
    )

    result = response.json()

    if "errors" in result:
        console.print("[yellow]Glossary term already exists.[/]")

    return "urn:li:glossaryTerm:stale-data-do-not-use"


def add_glossary_terms(blast_radius, term_urn):

    for node in blast_radius:
        variables = {"input": {"termUrn": term_urn, "resourceUrn": node["urn"]}}

        response = requests.post(
            GMS_URL,
            json={"query": ADD_GLOSSARY_TERM, "variables": variables},
            headers=headers,
        )

        result = response.json()

        if "errors" in result:
            console.print(f"[red]FAILED[/] {node['name']}")
        else:
            console.print(f"[green]TERM ADDED[/] {node['name']}")


def remove_glossary_terms(blast_radius, term_urn):

    for node in blast_radius:
        variables = {"input": {"termUrn": term_urn, "resourceUrn": node["urn"]}}

        response = requests.post(
            GMS_URL,
            json={"query": REMOVE_GLOSSARY_TERM, "variables": variables},
            headers=headers,
        )

        result = response.json()

        if "errors" in result:
            console.print(f"[red]REMOVE FAILED[/] {node['name']}")
        else:
            console.print(f"[green]TERM REMOVED[/] {node['name']}")


def resolve_datahub_incident(incident_urn):

    if incident_urn is None:
        return

    mutation = """
    mutation UpdateIncidentStatus(
        $urn: String!,
        $input: IncidentStatusInput!
    ) {
        updateIncidentStatus(
            urn: $urn,
            input: $input
        )
    }
    """

    variables = {"urn": incident_urn, "input": {"state": "RESOLVED"}}

    response = requests.post(
        GMS_URL,
        json={
            "query": mutation,
            "variables": variables,
        },
        headers=headers,
    )

    result = response.json()

    if "errors" in result:
        console.print(f"[bold red]FAILED TO RESOLVE INCIDENT:[/] {result['errors']}")
    else:
        console.print("[bold green]INCIDENT RESOLVED[/]")


import time


def ensure_freshness_assertion(dataset_urn, dataset_name):
    # Step 1: Look for an existing assertion attached to this dataset.
    response = requests.post(
        GMS_URL,
        json={
            "query": """
            query {
              searchAcrossEntities(
                input: {
                  types: [ASSERTION]
                  query: "*"
                  count: 100
                  start: 0
                }
              ) {
                searchResults {
                  entity {
                    urn

                    ... on Assertion {
                      info {
                        description
                      }

                      relationships(
                        input: {
                          types: []
                          direction: OUTGOING
                          start: 0
                          count: 5
                        }
                      ) {
                        relationships {
                          type

                          entity {
                            urn
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """
        },
        headers=headers,
    )

    response.raise_for_status()

    results = response.json()["data"]["searchAcrossEntities"]["searchResults"]

    for result in results:
        assertion = result["entity"]

        rels = assertion.get("relationships", {}).get("relationships", [])

        for rel in rels:
            if rel["type"] == "Asserts" and rel["entity"]["urn"] == dataset_urn:
                console.print(f"[green]Reusing assertion:[/] {assertion['urn']}")
                return assertion["urn"]

    # Step 2: None found -> create one.
    variables = {
        "input": {
            "entityUrn": dataset_urn,
            "type": "CUSTOM",
            "description": f"Ripple AI Freshness Monitor {dataset_name}",
            "platform": {"name": "Ripple AI"},
            "logic": "Dataset freshness must satisfy configured SLA.",
        }
    }

    response = requests.post(
        GMS_URL,
        json={
            "query": UPSERT_CUSTOM_ASSERTION,
            "variables": variables,
        },
        headers=headers,
    )

    response.raise_for_status()

    assertion_urn = response.json()["data"]["upsertCustomAssertion"]["urn"]

    console.print(f"[cyan]Created assertion:[/] {assertion_urn}")

    return assertion_urn


def report_assertion_result(assertion_urn, status):

    if assertion_urn is None:
        return False

    variables = {
        "urn": assertion_urn,
        "result": {
            "timestampMillis": int(time.time() * 1000),
            "type": status,
        },
    }

    response = requests.post(
        GMS_URL,
        json={
            "query": REPORT_ASSERTION_RESULT,
            "variables": variables,
        },
        headers=headers,
    )

    result = response.json()

    if "errors" in result:
        return False

    console.print(f"[green]ASSERTION {status} REPORTED[/]")

    return True


def wait_and_report_assertion(assertion_urn, status):

    MAX_WAIT_SECONDS = 10
    RETRY_INTERVAL = 0.25

    start = time.time()

    while True:
        if report_assertion_result(assertion_urn, status):
            elapsed = time.time() - start

            console.print(f"[green]Assertion became ready after {elapsed:.2f}s[/]")

            return True

        elapsed = time.time() - start

        if elapsed >= MAX_WAIT_SECONDS:
            raise RuntimeError(
                f"Assertion never became ready within {MAX_WAIT_SECONDS} seconds."
            )

        time.sleep(RETRY_INTERVAL)
