import json


def build_agent_context(context):

    return {
        "incident": {
            "dataset": context["target_table"],
            "gap_days": context["gap_days"],
        },
        "repair": {
            "source": context["source_table"],
            "target": context["target_table"],
            "timestamp_column": context["timestamp_column"],
        },
        "metadata": {
            "platform": "sqlite",
            "source_table": context["source_table"],
            "target_table": context["target_table"],
            "timestamp_column": context["timestamp_column"],
        },
    }
