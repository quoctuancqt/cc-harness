#!/usr/bin/env python3
"""PreToolUse hook: block edits that would give src/Domain or src/Application
a reference to Infrastructure or Presentation — the one rule CLAUDE.md marks
IMPORTANT/NEVER ("dependencies point inward only").

Heuristic, not a real analyzer: it text-matches the edit payload, so it can
false-positive on a comment or string that merely mentions the word. Exit 2
blocks the tool call and returns this message to Claude, which can then
either fix the design or, if it's a genuine false positive (e.g. a docstring
explaining the rule itself), rephrase to avoid the trigger words.
"""
import json
import re
import sys

PROTECTED_LAYER = re.compile(r"(^|/)src/(Domain|Application)(/|\.)")
FORBIDDEN_REF = re.compile(
    r"\busing\s+[\w.]*\b(Infrastructure|Presentation)\b"
    r"|\b(Infrastructure|Presentation)\.[A-Z]\w*"
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "").replace("\\", "/")

    if not file_path.endswith(".cs") or not PROTECTED_LAYER.search(file_path):
        return 0

    text = tool_input.get("content") or tool_input.get("new_string") or ""
    match = FORBIDDEN_REF.search(text)
    if not match:
        return 0

    print(
        f"Blocked: {file_path} is in Domain/Application but the edit references "
        f"'{match.group(0)}'. CLAUDE.md (Important Rules): dependencies point "
        "inward only — Domain/Application must never reference Infrastructure "
        "or Presentation. If this is a false positive (e.g. a comment), "
        "rephrase to avoid the literal word and retry.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
