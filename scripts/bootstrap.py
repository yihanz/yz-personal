#!/usr/bin/env python3
"""Apply stack.json to this machine: Claude Code, Codex, Homebrew and the daily updater.

Idempotent: re-running only adds what is missing and re-asserts auto-update.
Usage:  python3 scripts/bootstrap.py [--dry-run]
claude.ai and Cowork are configured in the web app; their list is printed at the end.
"""
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STACK = json.loads((ROOT / "stack.json").read_text())
DRY = "--dry-run" in sys.argv
HOME = pathlib.Path.home()
CODEX = shutil.which("codex") or "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"
CLAUDE = shutil.which("claude") or str(HOME / ".local/bin/claude")
ENV = dict(os.environ, DISABLE_TELEMETRY="1", HOMEBREW_NO_ANALYTICS="1")


def run(*cmd, ok_fail=False, read=False):
    """Run a command and return its stdout. A dry run only prints, except for
    read-only commands (read=True), which it runs so it can tell what is missing."""
    print("+", " ".join(cmd))
    if DRY and not read:
        return ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    except OSError as e:
        print(f"  ! not found: {cmd[0]} ({e.strerror})")
        if not ok_fail:
            sys.exit(127)
        return ""
    if r.returncode:
        print(f"  ! exit {r.returncode}: " + (r.stdout + r.stderr).strip()[-600:])
        if not ok_fail:
            sys.exit(r.returncode)
    return r.stdout


def jload(text):
    try:
        return json.loads(text or "[]")
    except ValueError:
        return []


def claude_code():
    cc = STACK["claude_code"]
    have = run(CLAUDE, "plugin", "marketplace", "list", "--json", ok_fail=True, read=True)
    known = {m.get("name") for m in jload(have)}
    for name, repo in cc["marketplaces"].items():
        if name not in known:
            run(CLAUDE, "plugin", "marketplace", "add", repo, ok_fail=True)
    installed = {p.get("id"): p for p in jload(run(CLAUDE, "plugin", "list", "--json", ok_fail=True, read=True))}
    added = [pid for pid in cc["plugins"] if pid not in installed]
    for pid in added:
        run(CLAUDE, "plugin", "install", pid, ok_fail=True)
    if added and not DRY:
        installed = {p.get("id"): p for p in jload(run(CLAUDE, "plugin", "list", "--json", ok_fail=True, read=True))}
    # Only switch a plugin that is in the wrong state: the CLI fails on "already enabled".
    # A fresh install starts enabled.
    for pid, enabled in cc["plugins"].items():
        if (pid in installed or DRY) and bool(installed.get(pid, {}).get("enabled", True)) != bool(enabled):
            run(CLAUDE, "plugin", "enable" if enabled else "disable", pid, ok_fail=True)
    # Auto-update is off by default for third-party marketplaces; assert it in user settings,
    # after the CLI has written its own entries.
    settings_path = HOME / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    ekm = settings.setdefault("extraKnownMarketplaces", {})
    for name, repo in cc["marketplaces"].items():
        ekm.setdefault(name, {})["source"] = {"source": "github", "repo": repo}
        ekm[name]["autoUpdate"] = True
    settings.setdefault("env", {}).update(cc.get("env", {}))
    if not DRY:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def codex():
    cx = STACK["codex"]
    if not os.path.exists(CODEX):
        print("Codex not found; skipping")
        return
    for name, repo in cx["marketplaces"].items():
        run(CODEX, "plugin", "marketplace", "add", repo, ok_fail=True)
    # `codex plugin list` prints "<id>  installed, enabled  ..." or "<id>  not installed  ...".
    have = set()
    for line in run(CODEX, "plugin", "list", ok_fail=True, read=True).splitlines():
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) > 1 and cols[1].startswith("installed"):
            have.add(cols[0])
    for pid in cx["plugins"]:
        if pid not in have:
            run(CODEX, "plugin", "add", pid, ok_fail=True)
    for s in cx["skills"]:
        cmd = ["npx", "-y", "skills@latest", "add", s["source"], "-g", "-a", "codex", "-y"]
        for name in s.get("skills", []):
            cmd += ["--skill", name]
        run(*cmd, ok_fail=True)


def brew_and_updater():
    if platform.system() != "Darwin":
        return
    brew = shutil.which("brew") or next(
        (b for b in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew") if os.access(b, os.X_OK)), None)
    if brew:
        run(brew, "install", *STACK["brew"], ok_fail=True)
    else:
        print("Homebrew not found; skipping " + ", ".join(STACK["brew"]))
    label = "com.yihan.agent-tools-update"
    plist = HOME / "Library/LaunchAgents" / f"{label}.plist"
    script = ROOT / "scripts" / "update_local.sh"
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array><string>/bin/zsh</string><string>{script}</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>7</integer></dict>
  <key>StandardOutPath</key><string>{HOME}/Library/Logs/agent-tools-update.log</string>
  <key>StandardErrorPath</key><string>{HOME}/Library/Logs/agent-tools-update.log</string>
</dict></plist>
"""
    print("+ write", plist)
    if not DRY:
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_text(body)
        uid = str(os.getuid())
        subprocess.run(["launchctl", "bootout", f"gui/{uid}/{label}"], capture_output=True)
        run("launchctl", "bootstrap", f"gui/{uid}", str(plist), ok_fail=True)


if __name__ == "__main__":
    if os.path.exists(CLAUDE):
        claude_code()
    else:
        print("Claude Code not found; skipping")
    codex()
    brew_and_updater()
    print("\nclaude.ai / Cowork (web app, Customize > Plugins > Add marketplace, then Sync automatically):")
    for repo in STACK["claude_ai"]["github_marketplaces"]:
        print("  -", repo)
    print("claude.ai / Cowork (Customize > Plugins > Discover, Anthropic's directory):")
    for name in STACK["claude_ai"].get("directory", []):
        print("  -", name)
