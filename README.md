# yz-personal

A plugin marketplace that carries agent skills whose authors publish no marketplace of their own, plus the install manifest and scripts that set up the rest of my agent tooling on a new machine.

## What it carries

| Plugin | Upstream | Skill |
|---|---|---|
| text-to-lottie | diffusionstudio/lottie | `skills/text-to-lottie` |
| no-ai-slop | petergyang/no-ai-slop | `skills/no-ai-slop` |
| unlazy | Leonxlnx/unlazy | repository root |
| cross-layer-drift-sweep | MiniMax-AI/minimax-code | `.agents/skills/cross-layer-drift-sweep` |
| database-lookup | K-Dense-AI/scientific-agent-skills | `skills/database-lookup` |
| scientific-critical-thinking | K-Dense-AI/scientific-agent-skills | `skills/scientific-critical-thinking` |
| figma-generate-project-plan | figma/mcp-server-guide | `workflow-skills/generate-project-plan` |
| figma-video-interaction-mapper | figma/mcp-server-guide | `workflow-skills/video-interaction-mapper` |

Nothing is copied into this repository. Each entry points at the upstream folder, pinned to the last upstream commit that touched it. A scheduled workflow (`.github/workflows/move-pins.yml`) moves the pins forward every day and records each move in `CHANGELOG.md`, so a subscriber receives upstream changes and the history shows exactly what changed and when.

## Subscribing

- Claude Code: `claude plugin marketplace add yihanz/yz-personal`, then `claude plugin install <name>@yz-personal`. Turn on auto-update for the marketplace (`/plugin` > Marketplaces), or let `scripts/bootstrap.py` set it.
- claude.ai and Cowork: Customize > Plugins > Add marketplace > `yihanz/yz-personal`, then turn on Sync automatically.
- Codex loads plugin skills only from a `skills/` folder, which these upstream folders lack, so Codex gets the same skills through `npx skills` instead (see `stack.json`).

## Setting up a machine

`stack.json` is the install manifest for every surface. On a Mac:

```
git clone https://github.com/yihanz/yz-personal ~/.claude-marketplaces/yz-personal
python3 ~/.claude-marketplaces/yz-personal/scripts/bootstrap.py
```

The bootstrap adds every marketplace to Claude Code with auto-update on, installs and enables the listed plugins, adds Codex marketplaces, plugins and skills, installs the Homebrew tools, and loads a LaunchAgent that runs `scripts/update_local.sh` daily, which upgrades the Homebrew tools, the `npx skills` installs, Claude Code plugins and Codex marketplaces. It prints the claude.ai marketplaces to add by hand.
