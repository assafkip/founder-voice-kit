#!/usr/bin/env python3
"""
voice-substance-lint.py - Positive-pattern voice enforcement (Layer 5).

The voice-lint hook catches deterministic AI fingerprints. It enforces what
NOT to do. But a draft can pass voice-lint and still read as AI cadence
because it has the SHAPE of voice (short declaratives, contrast pairs)
without any specific anchor. That's the cadence-without-substance failure
mode.

This script enforces presence of at least one anchor across three
categories for any prose over 200 words:

  1. WITNESS pattern: "I built", "I shipped", "I watched", "I ran",
     "I tested", "I engaged", etc.
  2. SPECIFIC NAMED ENTITY: a proper noun that is not sentence-initial
     and not a generic term (Google, LinkedIn, Q3, GPT-4)
  3. CONCRETE NUMBER: any digit string ($2k, 4 teams, 87%, 60 tools)

If the draft has ZERO of the three, it fires. Below 200 words the rule is
softer: requires at least 1 of the 3 above 80 words.

Stdlib only.

Usage:
    python3 voice-substance-lint.py <file_path>     # CLI
    python3 voice-substance-lint.py                 # hook (stdin JSON)

Exit codes:
    0 = clean (has substance)
    2 = violation (cadence-without-substance pattern detected)

Override:
    Add `<!-- voice-lint-skip -->` anywhere in the file to bypass.
"""

import json
import os
import re
import sys
from pathlib import Path


SKIP_MARKER = "voice-lint-skip"

CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
BLOCKQUOTE_RE = re.compile(r"^>\s.*$", re.MULTILINE)

WITNESS_PHRASES = [
    r"\bI built\b", r"\bI shipped\b", r"\bI watched\b", r"\bI ran\b",
    r"\bI tested\b", r"\bI engaged\b", r"\bI wanted to\b",
    r"\bI have been\b", r"\bI was in\b", r"\bI was at\b",
    r"\bI worked\b", r"\bI saw\b", r"\bI did\b", r"\bI tried\b",
    r"\bAt \w+,?\s+I\b", r"\bI noticed\b", r"\bI argue\b",
    r"\bI suggest\b", r"\bI spent\b", r"\bI walked\b",
    r"\bI checked\b", r"\bI hit\b", r"\bI rolled\b",
    r"\bI sat\b", r"\bI broke\b", r"\bI started\b",
    r"\bwhen I\b", r"\bafter I\b", r"\bbefore I\b",
    r"\bI used\b", r"\bI deployed\b", r"\bI fixed\b",
    r"\bI patched\b", r"\bI launched\b", r"\bI rewrote\b",
    r"\bI dropped\b", r"\bI added\b", r"\bI cut\b",
]

WORD_RE = re.compile(r"\b[\w'-]+\b")
NUMBER_RE = re.compile(r"\b\d[\d,\.]*\b")
PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-zA-Z0-9]{2,}\b")
SENTENCE_START_CAP_RE = re.compile(r'(?:\A|(?<=[.!?]\s)|(?<=\n\n))([A-Z])')

GENERIC_PROPER_NOUNS = {
    "Claude", "ChatGPT", "OpenAI", "Anthropic", "GitHub", "Linux",
    "Windows", "Python", "JavaScript", "TypeScript", "React",
    "AI", "API", "MCP", "URL", "JSON", "HTML", "CSS", "SQL",
    "True", "False", "None", "And", "But", "The", "This", "That",
    "When", "Where", "Why", "How", "What", "Who",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday", "January", "February", "March", "April",
    "May", "June", "July", "August", "September", "October",
    "November", "December", "PostToolUse", "PreToolUse", "UserPromptSubmit",
    "Edit", "Write", "MultiEdit",
}


def strip_code_for_prose_check(text):
    text = FRONTMATTER_RE.sub("", text)
    text = CODE_FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub(" ", text)
    text = BLOCKQUOTE_RE.sub("", text)
    return text


def word_count(text):
    return len(WORD_RE.findall(text))


def find_witness_matches(text):
    matches = []
    for pattern in WITNESS_PHRASES:
        for m in re.finditer(pattern, text):
            matches.append(m.group())
    return matches


def find_number_matches(text):
    return [m.group() for m in NUMBER_RE.finditer(text)]


def find_specific_proper_nouns(text):
    normalized = SENTENCE_START_CAP_RE.sub(lambda m: m.group(1).lower(), text)
    found = []
    for m in PROPER_NOUN_RE.finditer(normalized):
        word = m.group()
        if word in GENERIC_PROPER_NOUNS:
            continue
        found.append(word)
    return found


def lint_text(text):
    if SKIP_MARKER in text:
        return []
    prose = strip_code_for_prose_check(text)
    total_words = word_count(prose)
    if total_words < 80:
        return []
    witnesses = find_witness_matches(prose)
    numbers = find_number_matches(prose)
    proper_nouns = find_specific_proper_nouns(prose)
    has_witness = len(witnesses) >= 1
    has_number = len(numbers) >= 1
    has_proper = len(proper_nouns) >= 1
    anchor_count = sum([has_witness, has_number, has_proper])
    if total_words >= 200:
        if anchor_count == 0:
            return [{
                "rule": "no-substance-anchor",
                "detail": (
                    f"draft has {total_words} words but zero anchors. "
                    "Needs at least one of: witness phrase (I built/I shipped/...), "
                    "specific named entity (not generic), or concrete number. "
                    "Cadence without substance reads as AI."
                ),
            }]
    elif total_words >= 80:
        if anchor_count == 0:
            return [{
                "rule": "no-substance-anchor",
                "detail": (
                    f"draft has {total_words} words and zero anchors. "
                    "Add a witness phrase, named entity, or concrete number."
                ),
            }]
    return []


def format_report(file_path, violations):
    if not violations:
        return ""
    lines = [f"voice-substance-lint: {len(violations)} violation(s) in {file_path}:"]
    for v in violations:
        lines.append(f"  [{v['rule']}] {v['detail']}")
    lines.append("")
    lines.append("Add a real anchor or add <!-- voice-lint-skip --> to bypass (intentional exception only).")
    return "\n".join(lines)


def hook_mode():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)
    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path or not Path(file_path).exists():
        sys.exit(0)
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except Exception:
        sys.exit(0)
    violations = lint_text(text)
    if not violations:
        sys.exit(0)
    sys.stderr.write(format_report(file_path, violations) + "\n")
    sys.exit(2)


def cli_mode(file_path):
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"voice-substance-lint: read error: {e}\n")
        sys.exit(0)
    violations = lint_text(text)
    if not violations:
        print(f"voice-substance-lint: clean ({file_path})")
        sys.exit(0)
    print(format_report(file_path, violations))
    sys.exit(2)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        hook_mode()
    elif len(sys.argv) == 2:
        cli_mode(sys.argv[1])
    else:
        sys.stderr.write("Usage: voice-substance-lint.py <file_path>\n")
        sys.exit(1)
