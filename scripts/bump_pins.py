#!/usr/bin/env python3
"""Move each plugin's upstream pin to the last upstream commit that touched it.

For a git-subdir source the pin is the newest commit on `ref` that changed `path`,
so unrelated commits in a large monorepo do not register as updates. For a
whole-repository url source it is the head of `ref`.

Writes the new pins into .claude-plugin/marketplace.json, appends one line per
change to CHANGELOG.md, and prints a commit message to stdout. Exits 0 with no
output when nothing moved. Uses only git and the standard library.
"""
import datetime
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CHANGELOG = ROOT / "CHANGELOG.md"


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def latest(url, ref, path, cache):
    key = (url, ref)
    if key not in cache:
        d = tempfile.mkdtemp(prefix="pin-")
        git("clone", "--quiet", "--filter=blob:none", "--no-checkout", "--single-branch", "--branch", ref, url, d)
        cache[key] = d
    d = cache[key]
    args = ["log", "-1", "--format=%H%x09%cs%x09%s", "HEAD"]
    if path:
        args += ["--", path]
    out = git(*args, cwd=d)
    if not out:
        raise SystemExit(f"no commit found for {url} {path or '(root)'}; path moved or deleted upstream")
    sha, date, subject = out.split("\t", 2)
    return sha, date, subject


def main():
    data = json.loads(MARKETPLACE.read_text())
    cache, changes = {}, []
    for plugin in data["plugins"]:
        src = plugin.get("source")
        if not isinstance(src, dict) or src.get("source") not in ("git-subdir", "url"):
            continue
        sha, date, subject = latest(src["url"], src.get("ref", "main"), src.get("path", ""), cache)
        if sha != src.get("sha"):
            old = (src.get("sha") or "none")[:7]
            src["sha"] = sha
            changes.append(f"{plugin['name']} {old} -> {sha[:7]} ({date}: {subject})")
    if not changes:
        return 0
    MARKETPLACE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    today = datetime.date.today().isoformat()
    lines = "".join(f"- {today} · {c}\n" for c in changes)
    text = CHANGELOG.read_text() if CHANGELOG.exists() else "# Changelog\n\n"
    head, sep, rest = text.partition("## Upstream pin moves\n\n")
    if sep:
        CHANGELOG.write_text(head + sep + lines + rest)
    else:
        CHANGELOG.write_text(text.rstrip("\n") + "\n\n## Upstream pin moves\n\n" + lines)
    msg = "Move upstream pins: " + ", ".join(c.split(" (")[0] for c in changes)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
