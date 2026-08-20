#!/usr/bin/env python3
"""
voice-lint.py - Deterministic voice rule enforcer (Founder Voice Kit, Layer 3).

PostToolUse hook for Claude Code Edit / Write / MultiEdit calls.
Loads its config from ../config/ using only the Python standard library so the
buyer never has to pip install anything.

Usage:
    python3 voice-lint.py <file_path>     # CLI mode
    python3 voice-lint.py                 # hook mode (reads JSON from stdin)

Exit codes:
    0 = clean
    2 = violations found (PostToolUse contract -- Claude must fix)

Override:
    Add `<!-- voice-lint-skip -->` anywhere in the file to bypass entirely.
"""

import json
import os
import re
import sys
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


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

CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
BLOCKQUOTE_RE = re.compile(r"^>\s.*$", re.MULTILINE)
EMDASH_RE = re.compile(r"—")

NON_CONTRACTED_NEGATIONS = [
    r"\b(do not)\b", r"\b(does not)\b", r"\b(did not)\b",
    r"\b(is not)\b", r"\b(are not)\b", r"\b(was not)\b", r"\b(were not)\b",
    r"\b(have not)\b", r"\b(has not)\b", r"\b(had not)\b",
    r"\b(will not)\b", r"\b(would not)\b", r"\b(could not)\b",
    r"\b(should not)\b", r"\b(must not)\b",
    r"\b(can not)\b", r"\bcannot\b",
]

STAT_PATTERNS = [
    (re.compile(r"\b\d+\s*%"), "percentage figure"),
    (re.compile(r"\b\d+\s+percent\b", re.IGNORECASE), "percentage spelled out"),
    (re.compile(r"\b\d+x\s+(more|better|faster|higher)\b", re.IGNORECASE), "Xx multiplier claim"),
    (re.compile(r"according to (research|the survey|the study|a study)", re.IGNORECASE), "vendor-stat citation"),
    (re.compile(r"(survey|study|research) (found|showed|reported|revealed)", re.IGNORECASE), "vendor-stat citation"),
]


def load_text_list(filename):
    path = CONFIG_DIR / filename
    if not path.exists():
        return []
    entries = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def load_json(filename):
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def merge_text_overlay(base, local_filename):
    overlay = load_text_list(local_filename)
    if not overlay:
        return base
    return list({*base, *overlay})


def merge_json_overlay(base, local_filename):
    overlay = load_json(local_filename)
    if not overlay:
        return base
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = list({*merged[key], *value})
        else:
            merged[key] = value
    return merged


def load_config():
    words = merge_text_overlay(load_text_list("banned-words.txt"), "banned-words.local.txt")
    phrases = merge_text_overlay(load_text_list("banned-phrases.txt"), "banned-phrases.local.txt")
    structure = merge_json_overlay(load_json("structure-rules.json"), "structure-rules.local.json")
    slop_shapes = merge_json_overlay(load_json("slop-shapes.json"), "slop-shapes.local.json")
    paths = merge_json_overlay(load_json("published-paths.json"), "published-paths.local.json")
    return {
        "banned_words": set(words),
        "banned_phrases": phrases,
        "structure": structure,
        "slop_shapes": slop_shapes,
        "paths": paths,
    }


def is_published_path(file_path, paths_config):
    path_str = str(file_path)
    for pattern in paths_config.get("skip_paths", []):
        if glob_match(path_str, pattern):
            return False
    for pattern in paths_config.get("published_paths", []):
        if glob_match(path_str, pattern):
            return True
    return False


def strip_code_for_prose_check(text):
    text = FRONTMATTER_RE.sub("", text)
    text = CODE_FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("__CODE__", text)
    text = BLOCKQUOTE_RE.sub("", text)
    return text


def find_line_number(text, match_start):
    return text[:match_start].count("\n") + 1


def split_sentences(paragraph):
    parts = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    return [p.strip() for p in parts if p.strip()]


def first_word(sentence):
    match = re.search(r"\b([A-Za-z']+)\b", sentence)
    return match.group(1).lower() if match else None


def word_count(sentence):
    return len(re.findall(r"\b[\w'-]+\b", sentence))


def check_slop_shapes(text, config):
    """Templated shapes that cost reach. Each violation carries its replacement.

    Config-driven so a user whose own writing uses one of these can disable it. That
    escape hatch is not politeness: a list-based gate that catches its own author is
    the classic failure of this whole category, and the shipped defaults were only
    made blocking after being swept against a real 103-post corpus with zero hits.
    Run scripts/check-slop-shapes-against-corpus.py before trusting them on yours.
    """
    shapes_cfg = config.get("slop_shapes") or {}
    if not shapes_cfg.get("enabled", False):
        return []
    violations = []
    for shape in shapes_cfg.get("shapes", []):
        try:
            pattern = re.compile(shape["pattern"])
        except (KeyError, re.error):
            # A malformed user pattern degrades to "this rule is off", never to a
            # crash: a lint that dies on bad config blocks every write in the repo.
            continue
        found = pattern.search(text)
        if found:
            violations.append({
                "rule": shape.get("rule", "slop-shape"),
                "line": text[:found.start()].count(chr(10)) + 1,
                "detail": f"templated shape that costs reach: {found.group().strip()!r}. "
                          f"Write {shape.get('instead', 'it plainly instead')}",
            })
    return violations


def check_banned_words(text, config):
    violations = []
    prose_text = strip_code_for_prose_check(text)
    for word in config["banned_words"]:
        pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
        for match in pattern.finditer(prose_text):
            line = find_line_number(text, match.start())
            violations.append({"rule": "banned-word", "line": line, "detail": f"banned word: '{match.group()}'"})
    return violations


def check_banned_phrases(text, config):
    violations = []
    prose_text = strip_code_for_prose_check(text).lower()
    for phrase in config["banned_phrases"]:
        idx = prose_text.find(phrase.lower())
        while idx != -1:
            line = find_line_number(text, idx)
            violations.append({"rule": "banned-phrase", "line": line, "detail": f"banned phrase: '{phrase}'"})
            idx = prose_text.find(phrase.lower(), idx + 1)
    return violations


def check_emdash(text, config):
    if not config["structure"].get("flag_emdash", True):
        return []
    violations = []
    for match in EMDASH_RE.finditer(text):
        line = find_line_number(text, match.start())
        violations.append({"rule": "emdash", "line": line, "detail": "em dash (use comma, period, or hyphen instead)"})
    return violations


def check_contractions(text, config):
    if not config["structure"].get("flag_missing_contractions", True):
        return []
    violations = []
    prose_text = strip_code_for_prose_check(text)
    seen = set()
    for pattern in NON_CONTRACTED_NEGATIONS:
        regex = re.compile(pattern, re.IGNORECASE)
        for match in regex.finditer(prose_text):
            line = find_line_number(text, match.start())
            key = (line, match.group())
            if key in seen:
                continue
            seen.add(key)
            violations.append({
                "rule": "missing-contraction",
                "line": line,
                "detail": f"non-contracted negation '{match.group()}' (use the contracted form)",
            })
    return violations


def check_stats(text, config):
    if not config["structure"].get("flag_unsourced_stats", True):
        return []
    violations = []
    prose_text = strip_code_for_prose_check(text)
    for pattern, label in STAT_PATTERNS:
        for match in pattern.finditer(prose_text):
            line = find_line_number(text, match.start())
            violations.append({"rule": "stats-citation", "line": line, "detail": f"{label}: '{match.group()}'"})
    for citation in config["structure"].get("banned_stat_citations", []):
        pattern = re.compile(citation, re.IGNORECASE)
        for match in pattern.finditer(prose_text):
            line = find_line_number(text, match.start())
            violations.append({"rule": "stats-citation", "line": line, "detail": f"vendor-stat citation: '{match.group()}'"})
    return violations


def check_hedge_density(text, config):
    structure = config["structure"]
    prose_text = strip_code_for_prose_check(text)
    total_words = max(word_count(prose_text), 1)
    min_words = structure.get("min_word_count_for_hedge_check", 100)
    if total_words < min_words:
        return []
    hedge_words = structure.get("hedge_words", [])
    if not hedge_words:
        return []
    pattern = re.compile(r"\b(" + "|".join(re.escape(h) for h in hedge_words) + r")\b", re.IGNORECASE)
    hedges = pattern.findall(prose_text)
    ratio = len(hedges) / total_words
    threshold = structure.get("max_hedge_ratio", 0.002)
    min_hedges = structure.get("min_hedges_for_violation", 2)
    if ratio > threshold and len(hedges) >= min_hedges:
        return [{
            "rule": "hedge-density",
            "line": 1,
            "detail": f"hedge density {len(hedges)} hedges per {total_words} words (max {threshold}). Found: {hedges[:5]}{'...' if len(hedges) > 5 else ''}",
        }]
    return []


def check_single_sentence_paragraph(text, config):
    if not config["structure"].get("require_single_sentence_paragraph", True):
        return []
    prose_text = strip_code_for_prose_check(text)
    paragraphs = [p.strip() for p in prose_text.split("\n\n") if p.strip()]
    content_paragraphs = [p for p in paragraphs if not p.startswith("#")]
    if not content_paragraphs:
        return []
    for p in content_paragraphs:
        sentences = split_sentences(p)
        if len(sentences) == 1:
            return []
    return [{
        "rule": "no-single-sentence-paragraph",
        "line": 1,
        "detail": f"document has {len(content_paragraphs)} content paragraphs, none single-sentence. Voice DNA mandates at least one.",
    }]


def check_rule_of_three(text, config):
    """Detect three-of-a-kind sentence-opener patterns.

    v2 (Founder Voice Kit 0.2.0): adds density check across the whole
    document. The original consecutive-only check missed the common AI
    pattern of "The X. The Y. [longer]. [longer]. The Z." where the same
    opener appears at non-adjacent positions.
    """
    if not config["structure"].get("flag_rule_of_three", True):
        return []
    violations = []
    prose_text = strip_code_for_prose_check(text)
    paragraphs = prose_text.split("\n\n")
    # density check across the whole document
    all_sentences = []
    for para in paragraphs:
        all_sentences.extend(split_sentences(para))
    seen_density = set()
    if len(all_sentences) >= 5:
        from collections import Counter
        for start in range(len(all_sentences) - 4):
            window = all_sentences[start:start+5]
            firsts = [first_word(s) for s in window]
            counts = Counter(w for w in firsts if w)
            for word, c in counts.items():
                if c >= 3 and word not in seen_density:
                    seen_density.add(word)
                    violations.append({
                        "rule": "rule-of-three-density",
                        "line": 1,
                        "detail": f"opener '{word}' appears {c} times in a 5-sentence window starting at sentence {start+1}",
                    })
    cursor = 0
    for para in paragraphs:
        para_start = prose_text.find(para, cursor) if para else cursor
        if para_start == -1:
            para_start = cursor
        cursor = para_start + len(para)
        violations.extend(_rule_of_three_in_paragraph(text, para, para_start))
    return violations


def _rule_of_three_in_paragraph(text, para, para_start):
    sentences = split_sentences(para)
    violations = []
    for i in range(len(sentences) - 2):
        s1, s2, s3 = sentences[i], sentences[i+1], sentences[i+2]
        w1, w2, w3 = first_word(s1), first_word(s2), first_word(s3)
        if w1 and w1 == w2 == w3:
            line = find_line_number(text, para_start)
            violations.append({
                "rule": "rule-of-three",
                "line": line,
                "detail": f"three consecutive sentences start with '{w1}': '{s1[:40]}...' / '{s2[:40]}...' / '{s3[:40]}...'",
            })
            continue
        words = [word_count(s) for s in (s1, s2, s3)]
        if all(w <= 3 for w in words) and all(s.endswith(".") for s in (s1, s2, s3)):
            line = find_line_number(text, para_start)
            violations.append({
                "rule": "rule-of-three",
                "line": line,
                "detail": f"three consecutive single-noun sentences: '{s1}' / '{s2}' / '{s3}'",
            })
    return violations


def check_sentence_uniformity(text, config):
    structure = config["structure"]
    if not structure.get("flag_sentence_uniformity", True):
        return []
    violations = []
    prose_text = strip_code_for_prose_check(text)
    paragraphs = prose_text.split("\n\n")
    max_diff = structure.get("sentence_uniformity_max_diff", 1)
    min_len = structure.get("sentence_uniformity_min_length", 5)
    max_len = structure.get("sentence_uniformity_max_length", 18)
    cursor = 0
    for para in paragraphs:
        para_start = prose_text.find(para, cursor) if para else cursor
        if para_start == -1:
            para_start = cursor
        cursor = para_start + len(para)
        sentences = split_sentences(para)
        if len(sentences) < 3:
            continue
        for i in range(len(sentences) - 2):
            counts = [word_count(s) for s in sentences[i:i+3]]
            if max(counts) - min(counts) <= max_diff and min_len <= min(counts) <= max_len:
                line = find_line_number(text, para_start)
                violations.append({
                    "rule": "sentence-uniformity",
                    "line": line,
                    "detail": f"three consecutive sentences with uniform length ({counts} words): '{sentences[i][:40]}...'",
                })
                break
    return violations


def check_bold_restatement(text, config):
    if not config["structure"].get("flag_bold_restatement", True):
        return []
    violations = []
    bold_pattern = re.compile(r"\*\*([^*\n]{2,50})\*\*\s*[:\.]?\s*\n?([^\n]+)")
    for match in bold_pattern.finditer(text):
        bold_text = match.group(1).strip().rstrip(".:")
        following = match.group(2).strip()
        first_word_of_bold = first_word(bold_text)
        first_word_of_following = first_word(following)
        if first_word_of_bold and first_word_of_following == first_word_of_bold:
            line = find_line_number(text, match.start())
            violations.append({
                "rule": "bold-restatement",
                "line": line,
                "detail": f"bold title '**{bold_text}**' is restated in the following sentence (AI fingerprint)",
            })
    return violations


def lint_file(file_path):
    config = load_config()
    skip_marker = config["paths"].get("skip_marker", "voice-lint-skip")
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        return [{"rule": "read-error", "line": 0, "detail": str(e)}]
    if skip_marker in text:
        return []
    all_violations = []
    all_violations.extend(check_emdash(text, config))
    all_violations.extend(check_slop_shapes(text, config))
    all_violations.extend(check_banned_words(text, config))
    all_violations.extend(check_banned_phrases(text, config))
    all_violations.extend(check_stats(text, config))
    all_violations.extend(check_contractions(text, config))
    all_violations.extend(check_rule_of_three(text, config))
    all_violations.extend(check_sentence_uniformity(text, config))
    all_violations.extend(check_hedge_density(text, config))
    all_violations.extend(check_single_sentence_paragraph(text, config))
    all_violations.extend(check_bold_restatement(text, config))
    return all_violations


def format_report(file_path, violations):
    if not violations:
        return ""
    lines = [f"voice-lint: {len(violations)} violation(s) in {file_path}:"]
    violations.sort(key=lambda v: (v["line"], v["rule"]))
    for v in violations:
        lines.append(f"  line {v['line']} [{v['rule']}] {v['detail']}")
    lines.append("")
    lines.append("Fix in place, or add <!-- voice-lint-skip --> to bypass (intentional exception only).")
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
    if not file_path:
        sys.exit(0)
    config = load_config()
    if not is_published_path(file_path, config["paths"]):
        sys.exit(0)
    violations = lint_file(file_path)
    if not violations:
        sys.exit(0)
    sys.stderr.write(format_report(file_path, violations) + "\n")
    sys.exit(2)


def cli_mode(file_path):
    violations = lint_file(file_path)
    if not violations:
        print(f"voice-lint: clean ({file_path})")
        sys.exit(0)
    print(format_report(file_path, violations))
    sys.exit(2)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        hook_mode()
    elif len(sys.argv) == 2:
        cli_mode(sys.argv[1])
    else:
        sys.stderr.write("Usage: voice-lint.py <file_path>\n")
        sys.exit(1)
