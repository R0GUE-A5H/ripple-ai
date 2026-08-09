from mcp import ClientSession
from mcp.client.stdio import (
    stdio_client,
    StdioServerParameters,
)
from core.config import *


class MCPAgent:
    def __init__(self):

        self.server = StdioServerParameters(
            command="uvx",
            args=["mcp-server-datahub@latest"],
            env={
                "TOOLS_IS_MUTATION_ENABLED": "true",
                "DATAHUB_GMS_URL": DATAHUB_GMS_URL,
            },
        )

    async def list_tools(self):

        async with stdio_client(self.server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                return await session.list_tools()

    async def search(
        self,
        query,
    ):

        async with stdio_client(self.server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "search",
                    {
                        "query": query,
                    },
                )

            return result.structuredContent

    async def get_entities(
        self,
        urns,
    ):

        async with stdio_client(self.server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                return await session.call_tool(
                    "get_entities",
                    {
                        "urns": urns,
                    },
                )

    async def get_lineage(
        self,
        urn,
    ):

        async with stdio_client(self.server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                return await session.call_tool(
                    "get_lineage",
                    {
                        "urn": urn,
                    },
                )

    async def list_schema_fields(
        self,
        urn,
    ):

        async with stdio_client(self.server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                return await session.call_tool(
                    "list_schema_fields",
                    {
                        "urn": urn,
                    },
                )

    async def get_dataset_queries(
        self,
        urn,
    ):

        async with stdio_client(self.server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                return await session.call_tool(
                    "get_dataset_queries",
                    {
                        "urn": urn,
                    },
                )

    async def get_lineage_paths_between(
        self,
        source_urn,
        destination_urn,
    ):

        async with stdio_client(self.server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                return await session.call_tool(
                    "get_lineage_paths_between",
                    {
                        "source_urn": source_urn,
                        "destination_urn": destination_urn,
                    },
                )

    async def build_mcp_context(
        self,
        dataset_urn,
    ):

        entity = (await self.get_entities([dataset_urn])).structuredContent

        schema = (await self.list_schema_fields(dataset_urn)).structuredContent

        queries = (await self.get_dataset_queries(dataset_urn)).structuredContent

        entity_summary = {}

        try:
            dataset = entity["entities"][0]

            entity_summary = {
                "name": dataset.get("name"),
                "platform": dataset.get("platform", {}).get("name"),
                "description": dataset.get("properties", {}).get("description"),
                "owners": [
                    owner["owner"]["name"]
                    for owner in dataset.get("ownership", {}).get("owners", [])
                ],
                "tags": [
                    tag["tag"]["properties"]["name"]
                    for tag in dataset.get("tags", {}).get("tags", [])
                ],
                "glossary_terms": [
                    term["term"]["properties"]["name"]
                    for term in dataset.get("glossaryTerms", {}).get("terms", [])
                ],
            }

        except Exception:
            entity_summary = entity

        schema_summary = []

        try:
            fields = schema.get("fields", [])

            schema_summary = [
                {
                    "field": f.get("fieldPath"),
                    "type": f.get("nativeDataType"),
                }
                for f in fields
            ]

        except Exception:
            schema_summary = schema

        query_summary = []

        try:
            query_summary = queries.get("queries", [])[:3]

        except Exception:
            query_summary = queries

        return {
            "entity": entity_summary,
            "schema": schema_summary,
            "queries": query_summary,
        }

    async def save_document(
        self,
        document_type,
        title,
        content,
        topics=None,
        related_assets=None,
    ):

        async with stdio_client(self.server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "save_document",
                    {
                        "document_type": document_type,
                        "title": title,
                        "content": content,
                        "topics": topics,
                        "related_assets": related_assets,
                    },
                )

                return result
