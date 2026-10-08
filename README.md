# yz-personal

A plugin marketplace that carries agent skills whose authors publish no marketplace of their own, plus the install manifest and scripts that set up the rest of my agent tooling on a new machine.

## What it carries

Each plugin is one skill from one upstream repository. Adding the marketplace installs nothing: each plugin is installed, turned off, held or removed on its own.

| Plugin | Author | Upstream repository | Skill folder |
|---|---|---|---|
| no-ai-slop | Peter Yang | petergyang/no-ai-slop | `skills/no-ai-slop` |
| unlazy | Leon Lin | Leonxlnx/unlazy | repository root |
| design-qa | OpenAI | openai/plugins | `plugins/product-design/skills/design-qa` |
| visual-verdict | vibeeval | vibeeval/vibecosystem | `skills/visual-verdict` |
| cross-layer-drift-sweep | MiniMax | MiniMax-AI/minimax-code | `.agents/skills/cross-layer-drift-sweep` |
| verify-all-runtime-sinks | MiniMax | MiniMax-AI/minimax-code | `.agents/skills/verify-all-runtime-sinks` |
| database-lookup | K-Dense | K-Dense-AI/scientific-agent-skills | `skills/database-lookup` |
| scientific-critical-thinking | K-Dense | K-Dense-AI/scientific-agent-skills | `skills/scientific-critical-thinking` |
| figma-generate-project-plan | Figma | figma/mcp-server-guide | `workflow-skills/generate-project-plan` |
| figma-video-interaction-mapper | Figma | figma/mcp-server-guide | `workflow-skills/video-interaction-mapper` |
| text-to-lottie | Diffusion Studio | diffusionstudio/lottie | `skills/text-to-lottie` |

Nothing is copied into this repository. Each entry points at its upstream source and names the one skill it loads in `skills`. Ten use a `git-subdir` source at the folder that holds the skill, the form Anthropic's own marketplaces use for skill-only repositories (`learn-with-coursera` in `anthropics/knowledge-work-plugins`); sibling skills in that folder are not loaded. unlazy's skill is its repository root, so its entry is a `url` source with `skills: ["./"]`.

## How updates reach you

1. **Upstream to this repository.** `.github/workflows/move-pins.yml` runs daily. For each plugin it finds the newest upstream commit that changed that skill's folder, checks the plugin at that commit, and moves the pin only if the check passes. Each move is a commit here and a line in `CHANGELOG.md`.
2. **This repository to Claude.** A push here reaches claude.ai and Cowork at once when **Sync automatically** is on for the marketplace (a webhook on this repository), and otherwise when Claude next syncs or you select **Check for updates**. Updates install on your account with nothing to accept, and reach Claude Code as synced plugins.
3. **Claude Code on the Mac.** `scripts/update_local.sh` runs `claude plugin marketplace update` and `claude plugin update` daily.

## What the job checks before a pin moves

- **Forward only.** A pin moves only to a commit that descends from the current pin and changed the skill. If upstream history is rewritten (a force-push), the plugin stays on its pin and the run says so.
- **Skills only.** The plugin folder must hold the named `SKILL.md` with a name and description, and none of the default locations from which Claude loads anything else: `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `settings.json`, `monitors/monitors.json`, its own `.claude-plugin/plugin.json`, Markdown files anywhere under `agents/` or `commands/`, or anything under `bin/` (which claude.ai refuses to install), `output-styles/`, `workflows/`, `themes/` or a nested `skills/`. Names are compared without regard to case, and symbolic links and submodules are refused. An upstream that adds any of these stays on its last safe pin. A skill's own text can still ask Claude to do things, such as unlazy offering to install a Claude Code hook with your consent; the check covers what installs, not what a skill suggests.
- **Within limits.** At most 5,000 files per plugin, the claude.ai and Cowork limit.
- **Author channel.** When an upstream repository starts publishing its own Claude marketplace, the run says so: install from the author and remove the entry here.
- **One at a time.** A problem with one plugin never stops the others from moving. Any problem fails the run, and GitHub notifies the workflow's creator; the run summary names each plugin and why.
- **Kept alive.** GitHub turns off scheduled workflows in a public repository after 60 days without activity, so after 45 quiet days the job pushes an empty commit.
- **Checked on push.** A hand edit to the marketplace, `holds.json` or the job is checked as soon as it lands.

`python3 scripts/bump_pins.py --check` runs the same checks locally without changing anything.

## Choosing and customizing

- **Pick per plugin.** Install only the plugins you want; turn each off or remove it on its own in Customize > Plugins. Turning one off leaves the rest untouched.
- **Hold a version.** Add the plugin's name to `holds.json` (`{"no-ai-slop": "why"}`) and its pin stops moving while it is still checked. Remove the line to resume.
- **Change a skill's behavior.** Prefer layering: your own skills and preferences load beside a third-party skill and take precedence, so the upstream copy stays clean and keeps updating. When a change has to live inside the skill, fork the upstream repository and point that one entry's `url` at the fork; the job then follows the fork, and the other entries are unaffected.

## Subscribing

- Claude Code: `claude plugin marketplace add yihanz/yz-personal`, then `claude plugin install <name>@yz-personal`. Turn on auto-update for the marketplace (`/plugin` > Marketplaces), or let `scripts/bootstrap.py` set it.
- claude.ai and Cowork: Customize > Plugins > Add > Add marketplace > `yihanz/yz-personal`, turn on Sync automatically, then install the plugins you want one by one.
- Codex does not subscribe to this marketplace. `stack.json` lists what Codex gets instead: some of these skills through `npx skills`, others from OpenAI's curated directory.

## Setting up a machine

`stack.json` is the install manifest for every surface. On a Mac:

```
git clone https://github.com/yihanz/yz-personal ~/.claude-marketplaces/yz-personal
python3 ~/.claude-marketplaces/yz-personal/scripts/bootstrap.py
```

The bootstrap adds every marketplace to Claude Code with auto-update on, installs and enables the listed plugins, adds Codex marketplaces, plugins and skills, installs the Homebrew tools, and loads a LaunchAgent that runs `scripts/update_local.sh` daily, which upgrades the Homebrew tools, the `npx skills` installs, Claude Code plugins and Codex marketplaces. It prints the claude.ai marketplaces to add by hand.
