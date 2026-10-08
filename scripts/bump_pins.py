#!/usr/bin/env python3
"""Keep every plugin in .claude-plugin/marketplace.json on the newest safe upstream commit.

Each plugin is handled on its own: a problem with one never stops the others.

For each plugin entry:
  1. Find the newest upstream commit on `ref` that changed the plugin's skill folders.
  2. Check the plugin at that commit (see check()). Only a commit that passes moves the pin.
  3. Notice when the upstream repository starts publishing its own Claude marketplace,
     which is the signal to install from the author and retire the entry here.

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
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CHANGELOG = ROOT / "CHANGELOG.md"
HOLDS = ROOT / "holds.json"

MAX_FILES = 5000  # claude.ai and Cowork accept at most 5,000 files per plugin (and 200 MB, far above any entry here)

# Paths, relative to the plugin root, that would add something other than skills.
# These plugins are meant to carry instructions only: no hooks, programs, agents,
# connectors or commands arriving through an automatic update.
FORBIDDEN_EXACT = {
    "hooks/hooks.json": "hooks, which run commands on the computer",
    ".mcp.json": "an MCP server",
    ".lsp.json": "a language server",
    "settings.json": "Claude Code settings",
    "monitors/monitors.json": "background monitors",
    ".claude-plugin/plugin.json": "its own plugin manifest, which conflicts with this entry",
}
FORBIDDEN_PREFIX = {
    "bin/": "a top-level bin/ folder, which claude.ai refuses to install",
}
FORBIDDEN_MD_DIRS = {
    "agents/": "subagents",
    "commands/": "commands",
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
    # Names only: asking for sizes would fetch every file one by one from a partial clone.
    listing = git("ls-tree", "-r", "--name-only", "--full-tree", sha, *([root] if root else []), cwd=d)
    names = {path[len(root) + 1:] if root else path for path in listing.splitlines()}
    if not names:
        return [f"its folder `{root or '(repository root)'}` does not exist at {sha[:7]}"]
    if len(names) > MAX_FILES:
        problems.append(f"{len(names)} files, over the {MAX_FILES}-file plugin limit")
    for rel, why in FORBIDDEN_EXACT.items():
        if rel in names:
            problems.append(f"now contains `{rel}`: {why}")
    for prefix, why in FORBIDDEN_PREFIX.items():
        if any(n.startswith(prefix) for n in names):
            problems.append(f"now contains {why}")
    for prefix, why in FORBIDDEN_MD_DIRS.items():
        if any(n.startswith(prefix) and n.endswith(".md") and n.count("/") == 1 for n in names):
            problems.append(f"now contains {why} in `{prefix}`")
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


def upstream_marketplace(d, ref):
    try:
        git("cat-file", "-e", f"origin/{ref}:.claude-plugin/marketplace.json", cwd=d)
        return True
    except RuntimeError:
        try:
            git("cat-file", "-e", "HEAD:.claude-plugin/marketplace.json", cwd=d)
            return True
        except RuntimeError:
            return False


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
            if upstream_marketplace(d, ref):
                problems.append((name, f"{src['url']} now publishes its own Claude marketplace: "
                                       "install from the author and remove this entry"))
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
            found = check(repos, d, plugin, src, sha)
            if found:
                problems.append((name, f"upstream {sha[:7]} ({date}) not taken, staying on {current[:7]}: "
                                       + "; ".join(found)))
                continue
            src["sha"] = sha
            moves.append(f"{name} {current[:7]} -> {sha[:7]} ({date}: {subject})")
        except Exception as e:  # one plugin's failure never blocks the others
            problems.append((name, f"could not be checked: {e}"))

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
    report(problems)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
