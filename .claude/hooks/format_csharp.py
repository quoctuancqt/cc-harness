#!/usr/bin/env python3
"""PostToolUse hook: auto-format a .cs file with `dotnet format` right after
Claude edits it, so the Coding Rules / .editorconfig conventions in CLAUDE.md
are applied automatically instead of relying on Claude to remember them.

Best-effort and silent: never blocks the tool call that triggered it.
"""
import json
import os
import shutil
import subprocess
import sys


def find_solution_root(start: str) -> str | None:
    current = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(current, "global.json")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".cs"):
        return 0

    if not shutil.which("dotnet"):
        return 0

    root = find_solution_root(os.path.dirname(file_path) or ".")
    if root is None:
        return 0

    try:
        subprocess.run(
            ["dotnet", "format", "--include", file_path],
            cwd=root,
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
