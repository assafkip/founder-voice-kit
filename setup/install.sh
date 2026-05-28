#!/usr/bin/env bash
# install.sh - Founder Voice Kit installer
#
# Two-minute installer. Detects Claude Code, copies hooks + configs + skill
# into the project's .claude/ directory, and patches settings.json to wire
# the hooks to the right events.
#
# Usage (from the unzipped kit folder, inside your project):
#   bash setup/install.sh
#
# Requires: bash, python3, jq (the installer offers to install jq if missing)

set -euo pipefail

KIT_VERSION="0.1.0"

# Color output if terminal supports it
if [ -t 1 ]; then
    BOLD=$(tput bold || true)
    GREEN=$(tput setaf 2 || true)
    YELLOW=$(tput setaf 3 || true)
    RED=$(tput setaf 1 || true)
    RESET=$(tput sgr0 || true)
else
    BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

say() { printf "%s\n" "$1"; }
ok()  { printf "%s✓%s %s\n" "$GREEN" "$RESET" "$1"; }
warn(){ printf "%s!%s %s\n" "$YELLOW" "$RESET" "$1"; }
die() { printf "%s✗%s %s\n" "$RED" "$RESET" "$1" >&2; exit 1; }

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

detect_claude_code() {
    if [ -d ".claude" ]; then
        ok "found existing .claude directory"
        return 0
    fi
    if command -v claude >/dev/null 2>&1; then
        warn "claude CLI installed but no .claude directory in this folder"
        warn "running 'claude /init' once will create one. Aborting install."
        die "run 'claude /init' first, then retry"
    fi
    die "Claude Code not detected. Install it from claude.com/code first."
}

stage_files() {
    local target_dir="$1"

    mkdir -p "$target_dir/hooks"
    mkdir -p "$target_dir/voice-kit-config"
    mkdir -p "$target_dir/skills/founder-voice/references"

    say ""
    say "${BOLD}Staging files into $target_dir${RESET}"

    if [ -d "hooks" ] && [ -d "config" ] && [ -d "skills" ]; then
        cp hooks/voice-*.py "$target_dir/hooks/"
        cp config/*.txt config/*.json "$target_dir/voice-kit-config/"
        cp skills/founder-voice/SKILL.md "$target_dir/skills/founder-voice/"
        cp skills/founder-voice/references/*.template.md "$target_dir/skills/founder-voice/references/"
    else
        die "this script expects to run from the voice-kit repo root"
    fi

    chmod +x "$target_dir/hooks/"voice-*.py
    ok "files staged"
}

patch_settings() {
    local target_dir="$1"
    local settings="$target_dir/settings.json"

    if [ ! -f "$settings" ]; then
        echo "{}" > "$settings"
    fi

    if ! command -v jq >/dev/null 2>&1; then
        warn "jq not installed. Showing the settings.json snippet to merge by hand:"
        cat <<EOF
${YELLOW}---add to .claude/settings.json---${RESET}
{
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 $target_dir/hooks/voice-marker.py"}]}],
    "PreToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "python3 $target_dir/hooks/voice-gate.py"}]}],
    "PostToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [
      {"type": "command", "command": "python3 $target_dir/hooks/voice-lint.py"},
      {"type": "command", "command": "python3 $target_dir/hooks/voice-substance-lint.py"}
    ]}],
    "Stop": [{"hooks": [{"type": "command", "command": "python3 $target_dir/hooks/voice-stop-gate.py"}]}]
  }
}
EOF
        return 0
    fi

    local tmp
    tmp=$(mktemp)
    jq --arg dir "$target_dir" '
        .hooks.UserPromptSubmit = (.hooks.UserPromptSubmit // []) + [{
            "hooks": [{"type": "command", "command": "python3 \($dir)/hooks/voice-marker.py"}]
        }]
        | .hooks.PreToolUse = (.hooks.PreToolUse // []) + [{
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [{"type": "command", "command": "python3 \($dir)/hooks/voice-gate.py"}]
        }]
        | .hooks.PostToolUse = (.hooks.PostToolUse // []) + [{
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [
                {"type": "command", "command": "python3 \($dir)/hooks/voice-lint.py"},
                {"type": "command", "command": "python3 \($dir)/hooks/voice-substance-lint.py"}
            ]
        }]
        | .hooks.Stop = (.hooks.Stop // []) + [{
            "hooks": [{"type": "command", "command": "python3 \($dir)/hooks/voice-stop-gate.py"}]
        }]
    ' "$settings" > "$tmp"
    mv "$tmp" "$settings"
    ok "wired hooks in $settings"
}

print_next_steps() {
    local target_dir="$1"
    say ""
    say "${BOLD}${GREEN}Install complete.${RESET}"
    say ""
    say "Next steps:"
    say "  1. Edit ${BOLD}$target_dir/skills/founder-voice/references/voice-dna.template.md${RESET}"
    say "  2. Save it as voice-dna.md (drop the .template)"
    say "  3. Do the same with writing-samples.template.md"
    say "  4. Restart Claude Code so it picks up the new hooks"
    say "  5. Ask Claude to write you a LinkedIn post. Watch it iterate."
    say ""
    say "Full walkthrough: ${BOLD}setup/quickstart.md${RESET}"
}

main() {
    require_command python3

    say "${BOLD}Founder Voice Kit ${KIT_VERSION}${RESET}"
    say "Installing into the current project."
    say ""

    detect_claude_code

    local target_dir=".claude"
    stage_files "$target_dir"
    patch_settings "$target_dir"
    print_next_steps "$target_dir"
}

main "$@"
