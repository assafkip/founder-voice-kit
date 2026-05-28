<!-- voice-lint-skip -->
# Quickstart - 5 minutes to your first voice-locked draft

You bought the kit. Now make it work.

This guide is short on purpose. If you want the full per-OS walkthrough, see `setup/mac.md`, `setup/linux.md`, or `setup/windows.md`.

If you do not want to touch a terminal at all, skip this file and use `paste-into-claude.md` instead. That's Track B and it works without any install.

## Before you start

You need:
- Claude Code installed (see claude.com/code if not)
- Python 3.7 or later (Claude Code ships with this)
- Your project folder where you write content

That's it. No PyYAML. No pip install anything. No npm. Nothing.

## The two-minute install

From inside your project folder, run:

```bash
bash setup/install.sh
```

The script will:
1. Detect that Claude Code is installed.
2. Copy the 4 hook scripts into `.claude/hooks/`.
3. Copy the 4 config files into `.claude/voice-kit-config/`.
4. Copy the founder-voice skill into `.claude/skills/founder-voice/`.
5. Patch your `.claude/settings.json` to wire the hooks to the right events.
6. Print one line telling you what to do next.

If you don't trust `curl | bash` (smart instinct), the manual install lives in `setup/mac.md` and friends.

## The five-minute setup

Open your project. You'll find a new file:

```
.claude/skills/founder-voice/references/voice-dna.template.md
```

Copy it to `voice-dna.md` (drop the `.template`). Fill in every section. Generic answers produce generic output. Specific answers produce voice-locked drafts.

Then do the same with `writing-samples.template.md`. Paste 3 to 5 pieces of your actual writing.

Save both. The hooks read from these the first time a writing request fires.

## Test it works

Open a new Claude Code session in this project. Type:

> "write me a short LinkedIn post about why hooks beat instructions"

If voice-marker fired, you'll see a system note in the response about the founder-voice skill loading.

If voice-lint fires (it should, on the first draft from a fresh Claude), the output will block until the draft passes. Watch Claude iterate until clean. That's the kit working.

## Troubleshooting

- **Nothing fires:** check `.claude/settings.json` has the hook entries. If install.sh skipped that step, see `setup/troubleshooting.md`.
- **Lint fires on files it shouldn't:** edit `config/published-paths.json` to remove patterns or add to `skip_paths`.
- **Lint fires too aggressively:** edit `config/structure-rules.json`. Toggle individual `flag_*` keys to false.
- **You want to skip a specific file:** add `<!-- voice-lint-skip -->` anywhere in the file.

## Where to go next

- Want to see the kit in action before you set up your own voice? Read `examples/worked-example/`.
- Want the full Loom walkthrough? Watch the 5-minute video linked in your Gumroad receipt.
- Want to extend the banned-word list? Edit `config/banned-words.local.txt`. The local files merge on top of the defaults and are gitignored.
