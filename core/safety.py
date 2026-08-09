import ast
from pathlib import Path
import shutil
import subprocess
import tempfile

from rich.console import Console

from core.config import *
from core.constants import *
from core.graphql import *

console = Console()

SAFE_IMPORTS = {
    "sqlite3",
    "logging",
    "datetime",
    "time",
    "os",
    "sys",
    "pathlib",
    "contextlib",
    "typing",
    "collections",
    "itertools",
    "math",
}

FORBIDDEN_IMPORTS = {
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "http",
    "ftplib",
    "paramiko",
    "pickle",
    "marshal",
    "ctypes",
    "multiprocessing",
    "shutil",
    "glob",
}
FORBIDDEN_CALLS = {
    "exec",
    "eval",
    "compile",
    "__import__",
    "input",
}

FORBIDDEN_SQL = {
    "DROP TABLE",
    "ALTER TABLE",
    "ATTACH DATABASE",
    "DETACH DATABASE",
    "VACUUM",
    "PRAGMA",
}


def validate_generated_script(script_path):
    script_path = Path(script_path)

    code = script_path.read_text(encoding="utf-8")

    compile(code, script_path, "exec")
    console.print("[green]PYTHON SYNTAX OK[/]")


def safety_validate_generated_script(script_path):

    script_path = Path(script_path)

    code = script_path.read_text(encoding="utf-8")

    tree = ast.parse(code)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]

                if root in FORBIDDEN_IMPORTS:
                    raise RuntimeError(f"Unsafe import detected: {root}")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]

                if root in FORBIDDEN_IMPORTS:
                    raise RuntimeError(f"Unsafe import detected: {root}")

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    raise RuntimeError(f"Unsafe builtin detected: {node.func.id}")

    console.print("[green]SAFETY CHECK PASSED[/]")


import re


def validate_generated_sql(
    script_path,
    source_table,
    target_table,
):

    script_path = Path(script_path)

    code = script_path.read_text(
        encoding="utf-8",
    )

    upper = code.upper()

    for stmt in FORBIDDEN_SQL:
        if stmt in upper:
            raise RuntimeError(f"Forbidden SQL detected: {stmt}")

    tree = ast.parse(code)

    sql_strings = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = None

        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        elif isinstance(node.func, ast.Name):
            func_name = node.func.id

        if func_name not in (
            "execute",
            "executemany",
            "executescript",
        ):
            continue

        if not node.args:
            continue

        first_arg = node.args[0]

        if isinstance(first_arg, ast.Constant):
            if isinstance(first_arg.value, str):
                sql_strings.append(first_arg.value)

    tables = set()

    pattern = re.compile(
        r"""
        (?:FROM|JOIN|UPDATE|INTO|DELETE\s+FROM)
        \s+
        ([A-Za-z_][A-Za-z0-9_]*)
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    for sql in sql_strings:
        for table in pattern.findall(sql):
            tables.add(table)

    allowed_tables = {
        source_table.lower(),
        target_table.lower(),
    }

    illegal = {t.lower() for t in tables} - allowed_tables

    if illegal:
        raise RuntimeError(f"Generated repair touches unauthorized tables: {illegal}")

    console.print("[green]SQL SAFETY PASSED[/]")


def create_database_snapshot():

    snapshot = tempfile.NamedTemporaryFile(
        suffix=".db",
        delete=False,
    )

    shutil.copy(
        DATABASE_PATH,
        snapshot.name,
    )

    return snapshot.name


def restore_database_snapshot(snapshot_path):

    shutil.copy(
        snapshot_path,
        DATABASE_PATH,
    )

    console.print("[bold yellow]DATABASE RESTORED FROM SNAPSHOT[/]")


def apply_generated_repair(script_path):

    console.print("[cyan]SAFETY:[/] Creating database snapshot...")

    snapshot = create_database_snapshot()

    console.print("[green]Snapshot created.[/]")

    console.print("[cyan]APPLYING:[/] Running generated repair script...")

    result = subprocess.run(
        ["python", str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        console.print("[bold red]FAILED:[/] Repair script failed.")
        console.print(result.stderr)

        restore_database_snapshot(snapshot)

        return False, result.stderr

    console.print("[bold green]SUCCESS:[/] Repair script executed successfully.")
    console.print(result.stdout)

    return True, None
