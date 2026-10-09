#!/bin/zsh
# Daily: keep every locally installed agent tool current, whether or not an agent session runs.
# Claude Code (the CLI and its plugins) only auto-updates inside interactive sessions and Codex at
# app start, so this job makes updates happen on a schedule, and keeps every Mac that runs it on the
# same versions. Run by the com.yihan.agent-tools-update LaunchAgent.
export PATH="/opt/homebrew/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export DISABLE_TELEMETRY=1 HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_ENV_HINTS=1
ROOT="${0:A:h:h}"
CODEX="$(command -v codex || echo /Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex)"
echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z')"

git -C "$ROOT" pull --ff-only --quiet || echo "repo pull failed"

brew update --quiet && brew upgrade $(python3 -c "import json;print(' '.join(json.load(open('$ROOT/stack.json'))['brew']))") 2>&1 | tail -5

npx -y skills@latest update -g -y 2>&1 | tail -3

if command -v claude >/dev/null; then
  claude update 2>&1 | tail -2
  claude plugin marketplace update 2>&1 | tail -2
  python3 - "$ROOT/stack.json" <<'EOF' | while read -r pid; do claude plugin update "$pid" 2>&1 | tail -1; done
import json, sys
print("\n".join(json.load(open(sys.argv[1]))["claude_code"]["plugins"]))
EOF
fi

[ -x "$CODEX" ] && "$CODEX" plugin marketplace upgrade 2>&1 | tail -3
echo "=== done"
