#!/usr/bin/env python3
"""Keep every plugin in .claude-plugin/marketplace.json on the newest safe upstream commit.

Each plugin is handled on its own: a problem with one never stops the others.

For each plugin entry:
  1. Find the newest upstream commit on `ref` that changed the plugin's skill folders.
  2. Move only forward: that commit must descend from the current pin. Rewritten upstream
     history (a force-push) stays on the current pin and is reported.
  3. Check the plugin at that commit (see check()). Only a commit that passes moves the pin.
     A change to the tools a skill pre-approves (`allowed-tools`) also holds the pin for review.

holds.json lists plugins whose pin must not move (a deliberate freeze); they are still checked.

Usage:
  bump_pins.py            move pins, write marketplace.json and CHANGELOG.md, print a commit message
  bump_pins.py --check    check the current pins only; change nothing

Problems go to stderr and, under GitHub Actions, to the run summary. Exit status is 1 when any
problem was found, after every safe move has been written, so the run fails and notifies.
Uses only git and the Python standard library.
"""
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CHANGELOG = ROOT / "CHANGELOG.md"
HOLDS = ROOT / "holds.json"

MAX_FILES = 5000  # claude.ai and Cowork accept at most 5,000 files per plugin (and 200 MB, far above any entry here)

# The default locations, relative to the plugin root, from which Claude loads something other
# than the named skill (Claude Code plugins reference, "Standard layout"). Each plugin here is
# meant to deliver its one skill and nothing else, so an upstream that adds any of these does not
# move its pin. Names are compared case-insensitively, as macOS and Windows treat them.
FORBIDDEN_FILES = {
    "hooks/hooks.json": "hooks, which run commands on the computer",
    ".mcp.json": "an MCP server",
    ".lsp.json": "a language server",
    "settings.json": "Claude Code settings",
    "monitors/monitors.json": "background monitors",
    ".claude-plugin/plugin.json": "its own plugin manifest, which conflicts with this entry",
}
FORBIDDEN_FOLDERS = {  # folder: (what it would add, whether only .md files inside it load)
    "bin/": ("a top-level bin/ folder, which claude.ai refuses to install", False),
    "agents/": ("subagents", True),
    "commands/": ("commands", True),
    "output-styles/": ("output styles", False),
    "workflows/": ("workflows", False),
    "themes/": ("themes", False),
    "skills/": ("a skills/ folder, whose skills would load beside the named one", False),
}


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=900)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args[:3])} failed: {r.stderr.strip()[-300:]}")
    return r.stdout


class Repos:
    """One partial clone per upstream (url, ref), fetched on demand."""

    def __init__(self):
        self.cache = {}

    def get(self, url, ref):
        key = (url, ref)
        if key not in self.cache:
            d = tempfile.mkdtemp(prefix="pin-")
            git("clone", "--quiet", "--filter=blob:none", "--no-checkout", "--single-branch", "--branch", ref, url, d)
            self.cache[key] = d
        return self.cache[key]

    def cleanup(self):
        for d in self.cache.values():
            shutil.rmtree(d, ignore_errors=True)

    def ensure(self, d, sha):
        try:
            git("cat-file", "-e", f"{sha}^{{commit}}", cwd=d)
        except RuntimeError:
            git("fetch", "--quiet", "--filter=blob:none", "origin", sha, cwd=d)


def norm(*parts):
    """Join path parts into a repository-relative path: no leading ./ or /, no empty or . segments."""
    segs = []
    for part in parts:
        for seg in (part or "").split("/"):
            if seg not in ("", "."):
                segs.append(seg)
    return "/".join(segs)


def source_of(plugin):
    src = plugin.get("source")
    if not isinstance(src, dict) or src.get("source") not in ("git-subdir", "url"):
        return None
    return src


def skill_dirs(plugin):
    """Skill folders relative to the plugin root. No `skills` key means the root itself."""
    skills = plugin.get("skills") or ["./"]
    if isinstance(skills, str):
        skills = [skills]
    return [norm(s) for s in skills]


def watch_paths(plugin, src):
    root = src.get("path", "") if src["source"] == "git-subdir" else ""
    return [norm(root, s) or "." for s in skill_dirs(plugin)]


def allowed_tools(repos, d, plugin, src, sha):
    """The `allowed-tools` each named skill pre-approves at `sha`, as {skill folder: normalized value}."""
    root = norm(src.get("path", "")) if src["source"] == "git-subdir" else ""
    found = {}
    for s in skill_dirs(plugin):
        try:
            text = git("show", f"{sha}:{norm(root, s, 'SKILL.md')}", cwd=d)
        except RuntimeError:
            continue
        m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
        block = m.group(1) if m else ""
        value = re.search(r"^allowed-tools:[ \t]*(.*(?:\n[ \t]+-.*)*)", block, re.M)
        tools = re.findall(r"[A-Za-z0-9_][A-Za-z0-9_.:*()\[\]-]*", value.group(1)) if value else []
        found[s or "."] = " ".join(sorted(set(tools)))
    return found


def frontmatter_keys(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return set()
    return set(re.findall(r"^([A-Za-z0-9_-]+):", m.group(1), re.M))


def check(repos, d, plugin, src, sha):
    """Return a list of problems with this plugin at commit `sha`; empty means safe."""
    problems = []
    repos.ensure(d, sha)
    root = norm(src.get("path", "")) if src["source"] == "git-subdir" else ""
    # Names and modes only, NUL-separated so unusual file names arrive unquoted. Asking for
    # sizes would fetch every file one by one from a partial clone.
    listing = git("ls-tree", "-r", "-z", "--full-tree", sha, *([root] if root else []), cwd=d)
    entries = {}
    for item in listing.split("\0"):
        if not item:
            continue
        meta, path = item.split("\t", 1)
        entries[path[len(root) + 1:] if root else path] = meta.split()[0]
    if not entries:
        return [f"its folder `{root or '(repository root)'}` does not exist at {sha[:7]}"]
    names = set(entries)
    if len(names) > MAX_FILES:
        problems.append(f"{len(names)} files, over the {MAX_FILES}-file plugin limit")
    links = sorted(n for n, mode in entries.items() if mode in ("120000", "160000"))
    if links:
        problems.append(f"now contains a symbolic link or submodule (`{links[0]}`), which could point outside it")
    lower = {n.lower() for n in names}
    for rel, why in FORBIDDEN_FILES.items():
        if rel in lower:
            problems.append(f"now contains `{rel}`: {why}")
    for prefix, (why, md_only) in FORBIDDEN_FOLDERS.items():
        if any(n.startswith(prefix) and (n.endswith(".md") or not md_only) for n in lower):
            problems.append(f"now contains {why}")
    for s in skill_dirs(plugin):
        skill_md = norm(s, "SKILL.md")
        if skill_md not in names:
            problems.append(f"no SKILL.md at `{norm(root, s) or '.'}`")
            continue
        text = git("show", f"{sha}:{norm(root, skill_md)}", cwd=d)
        keys = frontmatter_keys(text)
        missing = {"name", "description"} - keys
        if missing:
            problems.append(f"`{norm(root, skill_md)}` lacks {', '.join(sorted(missing))} in its frontmatter")
    return problems


def is_ancestor(d, older, newer):
    r = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=d, capture_output=True, timeout=900)
    return r.returncode == 0


def report(problems):
    lines = [f"- **{name}**: {msg}" for name, msg in problems]
    for line in lines:
        print(line, file=sys.stderr)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and lines:
        with open(summary, "a") as f:
            f.write("### Plugins that need attention\n\n" + "\n".join(lines) + "\n")


def main():
    check_only = "--check" in sys.argv
    data = json.loads(MARKETPLACE.read_text())
    holds = json.loads(HOLDS.read_text()) if HOLDS.exists() else {}
    repos = Repos()
    moves, problems = [], []
    try:
        run(data, holds, repos, moves, problems, check_only)
    finally:
        repos.cleanup()
    write(data, moves)
    report(problems)
    return 1 if problems else 0


def run(data, holds, repos, moves, problems, check_only):
    for plugin in data["plugins"]:
        name = plugin.get("name", "?")
        src = source_of(plugin)
        if not src:
            continue
        try:
            ref = src.get("ref", "main")
            d = repos.get(src["url"], ref)
            current = src.get("sha")
            if not current:
                problems.append((name, "has no pinned sha"))
                continue
            for msg in check(repos, d, plugin, src, current):
                problems.append((name, f"current pin {current[:7]}: {msg}"))
            if check_only or name in holds:
                continue
            out = git("log", "-1", "--format=%H%x09%cs%x09%s", "HEAD", "--", *watch_paths(plugin, src), cwd=d).strip()
            if not out:
                problems.append((name, f"`{', '.join(watch_paths(plugin, src))}` no longer exists upstream; "
                                       f"staying on {current[:7]}"))
                continue
            sha, date, subject = out.split("\t", 2)
            if sha == current or is_ancestor(d, sha, current):
                continue  # the skill has not changed since the commit already pinned
            if not is_ancestor(d, current, sha):
                problems.append((name, f"upstream history was rewritten ({sha[:7]} does not descend from "
                                       f"{current[:7]}); staying on {current[:7]} until checked by hand"))
                continue
            found = check(repos, d, plugin, src, sha)
            before, after = allowed_tools(repos, d, plugin, src, current), allowed_tools(repos, d, plugin, src, sha)
            if before != after:
                shown = lambda v: "; ".join(x or "none" for x in v.values()) or "none"
                found.append(f"the tools it pre-approves changed from {shown(before)} to {shown(after)}; "
                             "review, then move the pin by hand")
            if found:
                problems.append((name, f"upstream {sha[:7]} ({date}) not taken, staying on {current[:7]}: "
                                       + "; ".join(found)))
                continue
            src["sha"] = sha
            moves.append(f"{name} {current[:7]} -> {sha[:7]} ({date}: {subject})")
        except Exception as e:  # one plugin's failure never blocks the others
            problems.append((name, f"could not be checked: {e}"))


def write(data, moves):
    if moves:
        MARKETPLACE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        today = datetime.date.today().isoformat()
        lines = "".join(f"- {today} · {m}\n" for m in moves)
        text = CHANGELOG.read_text() if CHANGELOG.exists() else "# Changelog\n\n"
        head, sep, rest = text.partition("## Upstream pin moves\n\n")
        if sep:
            CHANGELOG.write_text(head + sep + lines + rest)
        else:
            CHANGELOG.write_text(text.rstrip("\n") + "\n\n## Upstream pin moves\n\n" + lines)
        print("Move upstream pins: " + ", ".join(m.split(" (")[0] for m in moves))


if __name__ == "__main__":
    sys.exit(main())
