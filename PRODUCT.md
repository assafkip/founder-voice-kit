<!-- voice-lint-skip -->
# Founder Voice Kit - Product Spec

Version: 0.2.0
Status: shipped 2026-05-27 (v0.1.0), v0.2.0 same-day patch closing the chat-output gap
Owner: Assaf Kipnis

## What this product is

A Claude Code starter kit that ships in two installable tracks plus paid bundle assets. The buyer gets deterministic voice enforcement on every Edit and Write inside Claude Code, or a lower-fidelity paste-into-Claude version if they refuse to touch a terminal.

## What this product isn't

- Not a prompt template
- Not a system prompt
- Not a SaaS
- Not a fine-tuned model
- Not a generic anti-AI-detector evasion tool

It is a hook stack plus a paste-mode fallback. Local execution only.

## Architecture: two tracks, one thesis

### Track A: the five-layer hook stack (v0.2)

| Layer | Hook event | File | Job |
|---|---|---|---|
| 1. Marker | UserPromptSubmit | `hooks/voice-marker.py` | Detects when the user asks for written content (broad trigger list including counter, negotiate, pitch, message, send). Injects voice-skill reminder into context. |
| 2. Gate | PreToolUse (Edit, Write) | `hooks/voice-gate.py` | Pre-write check. Blocks if file path is published-content and the draft has obvious AI fingerprints (em dashes, banned words). |
| 3. Lint | PostToolUse (Edit, Write) | `hooks/voice-lint.py` | Full deterministic lint on written file. Wide path patterns, rule-of-three DENSITY check (catches non-consecutive same-opener patterns), uniformity floor dropped to 2 words. |
| 4. Substance Lint (NEW v0.2) | PostToolUse + Stop | `hooks/voice-substance-lint.py` | Positive-pattern enforcement. Requires at least one witness phrase, specific named entity, or concrete number on any prose over 80 words. Catches the cadence-without-substance failure mode. |
| 5. Stop-gate | Stop | `hooks/voice-stop-gate.py` | v0.2 expansion: re-lints files touched during turn AND lints the assistant's final chat message text. Closes the gap where chat-output drafts (the user copy-pastes to LinkedIn/X) were unguarded. |

Skill describes voice. Hooks enforce it. Neither is sufficient alone.

### Track B: paste-into-Claude (fallback)

A single markdown file: `paste-into-claude.md`. Contains:
- Voice DNA template inline
- Banned-word list inline
- Structure rule list inline
- Self-checking pre-publish prompt the buyer pastes alongside their draft

Claude runs the rules as instructions instead of as deterministic hooks. Lower fidelity. Catches obvious banned words, em dashes, and rule-of-three. Misses subtle uniformity violations the hook regex catches.

Frame for the buyer: "If you have Claude Code, install Track A. If you don't, paste Track B."

## Configuration surface

| File | Purpose |
|---|---|
| `config/banned-words.txt` | Banned word list with sensible defaults that the buyer extends. One word per line. |
| `config/banned-phrases.txt` | Banned phrase list shipped pre-populated, ready to customize. One phrase per line. |
| `config/structure-rules.json` | Sentence length max, hedge density, rule-of-three behavior. |
| `config/published-paths.json` | Glob patterns telling the linter where to fire. Override per your repo. |

All configs ship with sensible defaults. Buyer customizes by editing or by creating `.local.txt` / `.local.json` overlays (gitignored). Plain text and JSON were chosen over YAML so the kit has zero external Python dependencies.

## What ships in the public OSS portion

See `MANIFEST.md` for the file-level OSS / paid split.

- All four hook scripts (Track A)
- The paste-mode markdown (Track B)
- All four config files with defaults
- SKILL.md template
- voice-dna and writing-samples templates
- Minimal README

## What ships only in the paid Gumroad bundle

- Full setup guide for Mac, Linux, Windows
- The 5-minute Loom walkthrough
- Worked example with a fictional persona's filled-in voice DNA
- Receipts page with before/after samples
- Troubleshooting guide
- Future updates for 12 months

## Versioning

Semver. Public OSS and paid bundle share version numbers.

- 0.x: pre-launch and same-day-patch series
- 1.0: launch on Gumroad
- 1.x: add-only changes
- 2.0: hook contract changes (Claude Code API or breaking config schema)

### Changelog

**v0.2.0 (2026-05-28)** — same-day patch closing two structural gaps

- NEW: voice-substance-lint.py enforces presence of witness/named-entity/number anchors. Catches cadence-without-substance failures (drafts with voice shape but zero specific anchor).
- UPDATED: voice-stop-gate.py now lints the assistant's final chat message text in addition to files touched during the turn. The original v0.1 only re-linted files, leaving chat-output drafts unguarded.
- UPDATED: voice-lint.py adds rule-of-three DENSITY check (catches "The X. The Y. [...]. [...]. The Z." pattern at non-consecutive positions). Sentence-uniformity floor dropped from 5 to 2 words to catch short clipped declaratives.
- UPDATED: voice-marker.py trigger list expanded — counter, counter-offer, negotiate, pitch, proposal, message, send, ping, rebut, instagram, tiktok, reddit, hook, opener, closer, cta, voice, cadence, and "what should I write/say/send/reply" phrase patterns.
- UPDATED: published-paths.json wider glob patterns covering launch/, social/, marketing/, outreach/ and platform-prefixed files.

**v0.1.0 (2026-05-27)** — initial launch
- 4-layer hook stack
- Voice DNA + writing samples templates
- Paste-into-Claude fallback (Track B)
- One-line install script
- Mac/Linux/Windows setup guides

## Distribution model

- Public GitHub repo: OSS portion. MIT license. Stars accumulate as social proof.
- Gumroad paid bundle: zip of OSS + paid-only assets. $49 anchor, $29 / $79 price tests in weeks 4 and 8.
- Free lead magnet: email-gated single-script voice-lint download.

## Open spec items

- Exact filename of the buyer's local config (root `.voice-kit.yaml`? per-project override file?)
- Windows installation handling for Python path
- Whether the paid bundle includes a private GitHub mirror or just a Gumroad zip
- How the install script detects Claude Code presence and where it places hooks (`~/.claude/hooks/`? project-local?)
