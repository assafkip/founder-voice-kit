#!/usr/bin/env python3
"""
voice-gate.py - Pre-write fingerprint catcher (Founder Voice Kit, Layer 2).

PreToolUse hook for Claude Code Edit / Write / MultiEdit calls.

Cheap fast check that fires BEFORE the write hits disk. Looks at the proposed
content in the tool_input and blocks on the most obvious AI fingerprints:
em dashes, top banned words, and banned phrases. Lets the full lint run
PostToolUse for the deeper checks.

The job here is speed. Catch the smell early so Claude doesn't write a
guaranteed-violating file at all.

Scope: only fires on file paths matching published-paths.json.

Exit codes:
    0 = clean (write proceeds)
    2 = violation (write blocked, Claude must revise)
"""

import json
import re
import sys
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

EMDASH_RE = re.compile(r"—")


def glob_to_regex(pattern):
    """Translate a glob with ** to a regex. ** matches across slashes; * does not."""
    result = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                result.append(".*")
                i += 2
                if i < len(pattern) and pattern[i] == "/":
                    i += 1
            else:
                result.append("[^/]*")
                i += 1
        elif c == "?":
            result.append("[^/]")
            i += 1
        elif c in r".\+()[]^$|{}":
            result.append("\\" + c)
            i += 1
        else:
            result.append(c)
            i += 1
    return "^" + "".join(result) + "$"


def glob_match(path, pattern):
    return re.match(glob_to_regex(pattern), path) is not None

FAST_BANNED_WORDS = {
    "leverage", "robust", "transformative", "innovative", "cutting-edge",
    "groundbreaking", "delve", "synergy", "comprehensive", "utilize",
    "streamline", "revolutionize", "empower",
}

FAST_BANNED_PHRASES = [
    "in today's", "let's dive in", "game-changer", "game changer",
    "circling back", "just checking in", "excited to announce",
]


def load_json(filename):
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_published_path(file_path, paths_config):
    path_str = str(file_path)
    for pattern in paths_config.get("skip_paths", []):
        if glob_match(path_str, pattern):
            return False
    for pattern in paths_config.get("published_paths", []):
        if glob_match(path_str, pattern):
            return True
    return False


def extract_content(payload):
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    if tool_name == "Write":
        return tool_input.get("content", "")
    if tool_name == "Edit":
        return tool_input.get("new_string", "")
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits", [])
        return "\n".join(e.get("new_string", "") for e in edits)
    return ""


def find_violations(content):
    violations = []
    lower_content = content.lower()
    for word in FAST_BANNED_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", lower_content):
            violations.append(f"banned word '{word}'")
    for phrase in FAST_BANNED_PHRASES:
        if phrase in lower_content:
            violations.append(f"banned phrase '{phrase}'")
    if EMDASH_RE.search(content):
        violations.append("em dash (use comma, period, or hyphen)")
    return violations


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)
    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)
    paths_config = load_json("published-paths.json")
    if not is_published_path(file_path, paths_config):
        sys.exit(0)
    content = extract_content(payload)
    if not content:
        sys.exit(0)
    violations = find_violations(content)
    if not violations:
        sys.exit(0)
    sys.stderr.write(
        f"voice-gate: blocking {tool_name} on {file_path}. "
        f"{len(violations)} obvious AI fingerprint(s) in proposed content:\n"
    )
    for v in violations:
        sys.stderr.write(f"  - {v}\n")
    sys.stderr.write("Rewrite the content without these and try again.\n")
    sys.exit(2)


if __name__ == "__main__":
    main()
