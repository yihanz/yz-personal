# yz-personal

A plugin marketplace that carries agent skills whose authors offer no Claude route that updates on its own, plus the install manifest and scripts that set up the rest of my agent tooling on a new machine.

## Which route a third-party plugin takes

Each plugin comes through the most official route that keeps it current, preferring one that needs nobody to click **Check for updates**:

1. **Anthropic's directory**, when the author lists the plugin there (humanizer, Matt Pocock's skills). Anthropic reviews every version and claude.ai updates it on its own.
2. **The author's own marketplace**, when it demonstrably updates on its own in claude.ai. impeccable and taste-skill do: on 8 Oct 2026 impeccable took an upstream push about 15 minutes after it landed, and has taken 26 versions since 27 Sep. claude.ai refuses **Sync automatically** for a repository the Claude GitHub App cannot reach, and only the repository's owner can install the app there (humanizer's is refused).
3. **This marketplace**, for everything else: skills with no marketplace, and author marketplaces that do not update on their own (marketing-os). Claude Code keeps it current on its own. claude.ai does not yet act on pushes to an account marketplace even with Sync automatically on and the app installed ([anthropics/claude-code#93825](https://github.com/anthropics/claude-code/issues/93825); a push here on 8 Oct 2026 had not arrived 35 minutes later), so when pins move the job asks for **Check for updates** on a standing issue, and one click pulls every plugin here.

## What it carries

Each plugin is one skill from one upstream repository. Adding the marketplace installs nothing: each plugin is installed, turned off, held or removed on its own.

| Plugin | Author | Upstream repository | Skill folder |
|---|---|---|---|
| no-ai-slop | Peter Yang | petergyang/no-ai-slop | `skills/no-ai-slop` |
| marketing-os | Yuzzy Itaba | Yuzzyuk/marketing-os | `skills/marketing-os` |
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
| libraries-dev | Jakub Antalik | Jakubantalik/Libraries.dev | `skills/libraries-dev` |

Nothing is copied into this repository. Each entry points at exactly one upstream skill folder and declares it with `skills: ["./"]`: eleven are `git-subdir` sources at the skill's own folder, and unlazy, whose skill is its repository root, is a `url` source. Only that folder is fetched, so nothing else from the upstream repository is packaged or loaded. claude.ai lists each as one skill, and Claude Code loads each as one skill with no agents, hooks or connectors.

## How updates reach you

1. **Upstream to this repository.** `.github/workflows/move-pins.yml` runs daily. For each plugin it finds the newest upstream commit that changed that skill's folder, checks the plugin at that commit, and moves the pin only if the check passes. Each move is a commit here and a line in `CHANGELOG.md`.
2. **This repository to claude.ai and Cowork.** A push here arrives when you select **Check for updates** on the marketplace (Customize > Plugins > Add > Manage marketplaces). When the job moves pins, it comments on one standing issue, "Upstream changes waiting for Check for updates on claude.ai", assigned to the repository owner, so the notification comes exactly when there is something to pull. **Sync automatically** is on and will make the click unnecessary once claude.ai acts on pushes to account marketplaces ([anthropics/claude-code#93825](https://github.com/anthropics/claude-code/issues/93825)); then `scripts/ask_for_update.sh` and its workflow step can go. Updates install on your account with nothing to accept, and reach Claude Code as synced plugins.
3. **Claude Code on the Mac.** `scripts/update_local.sh` runs `claude plugin marketplace update` and `claude plugin update` daily.

## What the job checks before a pin moves

- **Forward only.** A pin moves only to a commit that descends from the current pin and changed the skill. If upstream history is rewritten (a force-push), the plugin stays on its pin and the run says so.
- **Skills only.** The plugin folder must hold the named `SKILL.md` with a name and description, and none of the default locations from which Claude loads anything else: `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `settings.json`, `monitors/monitors.json`, its own `.claude-plugin/plugin.json`, Markdown files anywhere under `agents/` or `commands/`, or anything under `bin/` (which claude.ai refuses to install), `output-styles/`, `workflows/`, `themes/` or a nested `skills/`. Names are compared without regard to case, and symbolic links and submodules are refused. An upstream that adds any of these stays on its last safe pin. A skill's own text can still ask Claude to do things, such as unlazy offering to install a Claude Code hook with your consent; the check covers what installs, not what a skill suggests.
- **Same permissions.** A skill's `allowed-tools` line lets it use those tools without asking. If an update changes that line, the pin stays where it is until you review it and move it by hand.
- **Within limits.** At most 5,000 files per plugin, the claude.ai and Cowork limit.
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

The bootstrap adds every marketplace to Claude Code with auto-update on, installs and enables the listed plugins, adds Codex marketplaces, plugins and skills, installs the Homebrew tools, and loads a LaunchAgent that runs `scripts/update_local.sh` daily, which upgrades the Homebrew tools, the `npx skills` installs, the Claude Code CLI and its plugins, and Codex marketplaces. It prints the claude.ai marketplaces to add by hand. Whatever is missing is skipped with a line saying so: no Claude Code CLI, no ChatGPT app (Codex), or no Homebrew (its formulas); the updater is installed either way. `--dry-run` reads what Claude Code already has and prints only the commands a real run would execute, changing nothing.
