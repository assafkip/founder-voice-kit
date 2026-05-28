#!/usr/bin/env python3
"""
voice-stop-gate.py - End-of-turn voice integrity check (Founder Voice Kit, Layer 4, v0.2).

Stop hook for Claude Code.

v0.2 expansion: also checks the assistant's final TEXT MESSAGE (chat output),
not just files touched during the turn. The original kit version only re-linted
files. Most drafts produced for the user to copy-paste live in chat output,
which file-only linting misses entirely. This version closes that gap.

Stdlib only. Re-uses voice-lint.py and voice-substance-lint.py via subprocess.

Exit codes:
    0 = clean (turn completes)
    2 = violation (turn blocked, Claude must re-draft)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parent
VOICE_LINT = HOOKS_DIR / "voice-lint.py"
VOICE_SUBSTANCE_LINT = HOOKS_DIR / "voice-substance-lint.py"

MIN_TEXT_BYTES = 80


def find_final_assistant_text(transcript_path):
    if not transcript_path or not Path(transcript_path).exists():
        return ""
    text_parts = []
    for line in Path(transcript_path).read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except Exception:
            continue
        message = record.get("message", {})
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        text_parts = []
        for item in message.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    text_parts.append(text)
            elif isinstance(item, str):
                text_parts.append(item)
    return "\n\n".join(text_parts)


def files_touched_this_turn(payload):
    transcript = payload.get("transcript_path")
    if not transcript or not Path(transcript).exists():
        return []
    touched = set()
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except Exception:
            continue
        tool_use = record.get("toolUseResult") or {}
        path = tool_use.get("filePath")
        if path:
            touched.add(path)
        message = record.get("message", {})
        for item in message.get("content", []) if isinstance(message, dict) else []:
            if not isinstance(item, dict):
                continue
            tool_input = item.get("input", {})
            path = tool_input.get("file_path")
            if path and item.get("name") in ("Edit", "Write", "MultiEdit"):
                touched.add(path)
    return list(touched)


def run_lint(script, file_path):
    if not script.exists():
        return (0, "")
    try:
        result = subprocess.run(
            ["python3", str(script), file_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return (result.returncode, result.stdout + result.stderr)
    except subprocess.TimeoutExpired:
        return (1, f"voice-stop-gate: {script.name} timed out on {file_path}")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    failures = []
    # check 1: re-lint any files touched during the turn
    files = files_touched_this_turn(payload)
    for file_path in files:
        if not Path(file_path).exists():
            continue
        code, output = run_lint(VOICE_LINT, file_path)
        if code == 2:
            failures.append(output)
        code2, output2 = run_lint(VOICE_SUBSTANCE_LINT, file_path)
        if code2 == 2:
            failures.append(output2)
    # check 2: lint the assistant's chat output text
    text = find_final_assistant_text(payload.get("transcript_path", ""))
    if len(text.encode("utf-8")) >= MIN_TEXT_BYTES:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(text)
            tmp_path = tmp.name
        try:
            code, output = run_lint(VOICE_LINT, tmp_path)
            if code == 2 and output:
                failures.append("chat output: " + output)
            code2, output2 = run_lint(VOICE_SUBSTANCE_LINT, tmp_path)
            if code2 == 2 and output2:
                failures.append("chat output: " + output2)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    if not failures:
        sys.exit(0)
    sys.stderr.write(
        f"voice-stop-gate: {len(failures)} violation(s) at turn end.\n"
        f"Fix before completing the turn:\n\n"
    )
    for output in failures:
        sys.stderr.write(output + "\n")
    sys.exit(2)


if __name__ == "__main__":
    main()
