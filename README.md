# Founder Voice Kit

Claude Code hooks that lock your writing voice so Claude stops sounding like AI.

Your last LinkedIn post sounded like Claude wrote it. You had a real idea. You opened Claude. What came back read fine and felt off. You rewrote it twice. The third draft still sounded like every other AI-assisted post on the timeline.

Better prompts do not fix this. The voice drifts back inside three drafts. The only thing that holds is a rule layer that runs between you and the file.

## What it is

The Founder Voice Kit is a Claude Code hook stack that locks your writing voice so Claude stops sounding like AI. Five Python hooks run locally on your machine. They check every draft for banned words, em dashes, rule-of-three patterns, and sentence uniformity, then block the ones that slip through. Your writing never leaves your machine. Stdlib only, no pip install.

## How to stop Claude from sounding like AI

Prompts ask. Hooks enforce. You can tell Claude to write in your voice. You cannot stop the drift unless something runs between the prompt and the file. The skill describes what good voice sounds like. The hook catches what the skill missed. That is how you lock your writing voice in Claude instead of re-fixing it every draft.

## How to make Claude write like you

You write a voice profile once. You fill in your banned words, your structure rules, and a few real writing samples. The hooks load that profile on every session and enforce it on every Edit and Write. No re-prompting. The first draft already sounds like you, because the beige version never makes it to disk.

## How it compares

| Approach | What it does | Holds across a session? |
|----------|--------------|-------------------------|
| System prompt / project instructions | Asks Claude to write like you | No. Drifts back in about three drafts. |
| Few-shot examples | Shows Claude your samples | No. Fades as the context window fills. |
| AI humanizer tool | Rewrites the output after the fact | No. Bolts on at the end, strips your meaning. |
| Voice Kit hook stack | Blocks the fingerprints before the file is written | Yes. Runs on every edit, every session. |

## What is in this repo (free, MIT)

- 5 Claude Code hook scripts: marker, gate, lint, substance-lint, stop-gate
- 4 config files with sensible defaults you extend: banned words, banned phrases, structure rules, published paths
- `paste-into-claude.md`: a zero-install fallback for when you do not want a terminal
- The founder-voice skill template plus the voice-DNA and writing-samples templates you fill in
- A quickstart and the one-line installer

This is the working system. Clone it, read it, change it.

## Install

### With Claude Code

From the unzipped folder, inside your project:

```bash
bash setup/install.sh
```

It detects your `.claude` folder, copies the hooks and configs, and patches `settings.json`. Two minutes.

### Without a terminal

Open `paste-into-claude.md`. Copy the whole file. Paste it into a Claude conversation. Lower fidelity than the full hook stack, but it catches the obvious offenders.

## The paid kit

This repo is the engine. The $49 kit on Gumroad adds the done-for-you parts: per-OS setup guides for Mac, Linux, and Windows, a full worked example with a filled-in voice profile, the receipts showing before and after drafts, a troubleshooting guide, and 12 months of updates as the AI patterns change.

Get it here: https://claudedaddy.gumroad.com/l/owdwj

## I build these for teams

I built this for myself first, then shipped the generic version. If you want one wired to your own stack and voice, that is what I do for teams. Grab a slot: https://calendar.app.google/cMFvhvDsfi9iyWYy9

## License

MIT for everything in this repo. See `LICENSE`.
