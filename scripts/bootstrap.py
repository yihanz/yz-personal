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


def run(*cmd, ok_fail=False):
    print("+", " ".join(cmd))
    if DRY:
        return ""
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if r.returncode and not ok_fail:
        print(r.stdout + r.stderr)
    return r.stdout


def claude_code():
    cc = STACK["claude_code"]
    have = run(CLAUDE, "plugin", "marketplace", "list", "--json", ok_fail=True)
    known = {m.get("name") for m in json.loads(have or "[]")} if not DRY else set()
    for name, repo in cc["marketplaces"].items():
        if name not in known:
            run(CLAUDE, "plugin", "marketplace", "add", repo, ok_fail=True)
    installed = {p["id"]: p for p in json.loads(run(CLAUDE, "plugin", "list", "--json", ok_fail=True) or "[]")} if not DRY else {}
    for pid, enabled in cc["plugins"].items():
        if pid not in installed:
            run(CLAUDE, "plugin", "install", pid, ok_fail=True)
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
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def codex():
    cx = STACK["codex"]
    if not os.path.exists(CODEX):
        print("Codex not found; skipping")
        return
    for name, repo in cx["marketplaces"].items():
        run(CODEX, "plugin", "marketplace", "add", repo, ok_fail=True)
    for pid in cx["plugins"]:
        run(CODEX, "plugin", "add", pid, ok_fail=True)
    for s in cx["skills"]:
        cmd = ["npx", "-y", "skills@latest", "add", s["source"], "-g", "-a", "codex", "-y"]
        for name in s.get("skills", []):
            cmd += ["--skill", name]
        run(*cmd, ok_fail=True)


def brew_and_updater():
    if platform.system() != "Darwin":
        return
    brew = shutil.which("brew") or "/opt/homebrew/bin/brew"
    run(brew, "install", *STACK["brew"], ok_fail=True)
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
        plist.write_text(body)
        uid = str(os.getuid())
        subprocess.run(["launchctl", "bootout", f"gui/{uid}/{label}"], capture_output=True)
        run("launchctl", "bootstrap", f"gui/{uid}", str(plist), ok_fail=True)


if __name__ == "__main__":
    if os.path.exists(CLAUDE):
        claude_code()
    codex()
    brew_and_updater()
    print("\nclaude.ai / Cowork (web app, Customize > Plugins > Add marketplace, then Sync automatically):")
    for repo in STACK["claude_ai"]["github_marketplaces"]:
        print("  -", repo)
