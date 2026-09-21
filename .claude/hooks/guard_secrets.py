#!/usr/bin/env python3
"""PreToolUse hook: block Claude from reading or writing secrets / production
config — .env files and appsettings.*Production*.json — so real credentials
never enter the conversation or get edited directly. Secrets belong in user
secrets / environment variables / a vault, not files Claude touches.
"""
import json
import os
import re
import sys

ENV_FILE = re.compile(r"^\.env(\..+)?$")
PROD_APPSETTINGS = re.compile(r"^appsettings\..*production.*\.json$", re.IGNORECASE)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return 0

    name = os.path.basename(file_path)
    if not (ENV_FILE.match(name) or PROD_APPSETTINGS.match(name)):
        return 0

    print(
        f"Blocked: {file_path} looks like a secrets/production config file. "
        "This template blocks Claude from reading or writing it directly — "
        "manage secrets via `dotnet user-secrets`, environment variables, or "
        "a vault instead.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
