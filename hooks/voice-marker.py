#!/usr/bin/env python3
"""
voice-marker.py - Voice skill reminder (Founder Voice Kit, Layer 1).

UserPromptSubmit hook for Claude Code.

When the user's prompt looks like a request for written content (post, email,
DM, article, comment, reply, draft), this hook injects a short reminder into
context so Claude loads the founder-voice skill before composing.

Stdlib only. No external dependencies.

Exit codes:
    0 = always (this hook only adds context, never blocks)
"""

import json
import re
import sys


WRITING_TRIGGER_PATTERNS = [
    # Direct write intents (v0.2: wildcard suffixes catch -ing, -ed forms)
    r"\bwrit\w*\b", r"\bdraft\w*\b", r"\bcompose\w*\b",
    r"\brewrite\w*\b", r"\brevise\w*\b", r"\bedit\w*\b",
    r"\bredraft\w*\b", r"\bredo\b", r"\bpolish\w*\b",
    # Content surfaces
    r"\bpost\b", r"\bemail\w*\b", r"\bdm\b", r"\bmessage\b", r"\bmsg\b",
    r"\breply\w*\b", r"\brespond\w*\b", r"\bcomment\w*\b", r"\bresponse\b",
    r"\barticle\b", r"\bessay\b", r"\bnewsletter\b",
    r"\bsend\b", r"\btext\b", r"\bping\b",
    # Platform-specific
    r"\blinkedin\b", r"\btwitter\b", r"\bmedium\b",
    r"\bsubstack\b", r"\bthread\b", r"\btweet\w*\b",
    r"\binstagram\b", r"\btiktok\b", r"\breddit\b",
    # Outreach / negotiation (v0.2: missing from v0.1)
    r"\boutreach\b", r"\bsales letter\b", r"\bcold email\b",
    r"\bcounter\b", r"\bcounter-?offer\b", r"\bnegotiat\w*\b",
    r"\bpitch\b", r"\bproposal\b", r"\boffer\b", r"\brebut\w*\b",
    # Structural elements
    r"\bcaption\b", r"\bheadline\b", r"\bsubject line\b",
    r"\bhook\b", r"\bopener\b", r"\bcloser\b", r"\bcta\b",
    # Meta intents
    r"\bvoice\b", r"\bcadence\b",
    r"\bwhat (should|do) I (write|say|send|reply)\b",
    r"\bcan you (write|draft|compose)\b",
]

REMINDER = (
    "[voice-kit] Writing request detected. Load the founder-voice skill "
    "(`skills/founder-voice/SKILL.md`) and its references "
    "(`voice-dna.md`, `writing-samples.md`) before composing. The voice-lint "
    "hook will block PostToolUse on banned words, em dashes, rule-of-three, "
    "and uniformity. Save iterations by drafting in-voice the first time."
)


def looks_like_writing_request(text):
    text_lower = text.lower()
    for pattern in WRITING_TRIGGER_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    user_prompt = payload.get("prompt", "")
    if not user_prompt:
        sys.exit(0)
    if not looks_like_writing_request(user_prompt):
        sys.exit(0)
    output = {"hookSpecificOutput": {"additionalContext": REMINDER}}
    sys.stdout.write(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
