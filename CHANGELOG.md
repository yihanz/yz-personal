# Changelog

The scheduled pin job writes one line per upstream change under "Upstream pin moves", newest first. Entries above it are changes to what this marketplace carries.

## Marketplace changes

- 2026-10-08 · Added libraries-dev, Jakub Antalik's skill for his seven Libraries.dev UI effect packages. Its author ships it through `npx skills` and his own CLI, with no Claude marketplace or directory listing, so this is its auto-updating Claude route; it is markdown only and passes every check. Its Voice reference still documents the `processing` prop that voice-glow 0.3.0 removed, and its React Native install lines name packages that are not on npm.
- 2026-10-08 · When pins move, the job now comments on one standing issue, assigned to the owner, asking for Check for updates on claude.ai, which does not yet act on pushes to an account marketplace (anthropics/claude-code#93825).
- 2026-10-08 · Added marketing-os, whose author marketplace does not update on its own in claude.ai; here it gets the job's checks and the same single Check for updates as every other entry. An upstream that publishes its own marketplace is no longer reported as a reason to leave this one, since that marketplace may not update on its own either.
- 2026-10-08 · Each entry now points at its skill's own folder with `skills: ["./"]`, so only that folder is packaged; claude.ai had been counting sibling skills' scripts against visual-verdict when the entries pointed at the parent folder. A change to the tools a skill pre-approves (`allowed-tools`) now holds its pin for review.
- 2026-10-08 · Each entry now names the one skill it loads; the ten `git-subdir` entries point at the folder that holds their skill, the form Anthropic's own marketplaces use, and unlazy stays a `url` source at its repository root. The pin job checks each plugin before moving it (skills only, within limits, forward only), handles each plugin on its own, honours holds in `holds.json`, flags upstreams that start publishing their own marketplace, keeps its schedule alive past GitHub's 60-day limit, and checks hand edits on push.
- 2026-10-08 · Added verify-all-runtime-sinks, the MiniMax companion to cross-layer-drift-sweep, so the uploaded account copy can go.
- 2026-10-08 · Added design-qa (OpenAI's Product Design helper, from openai/plugins, where OpenAI now publishes it after resetting openai/role-specific-plugins) and visual-verdict (the single skill from vibeeval/vibecosystem, without the rest of that bundle).
- 2026-10-05 · Moved from a local directory on the docked Mac to this repository, so Claude Code, Codex and claude.ai can all subscribe to it. Added no-ai-slop, unlazy, cross-layer-drift-sweep, database-lookup, scientific-critical-thinking, figma-generate-project-plan and figma-video-interaction-mapper. text-to-lottie lost its fixed "1.0.0" version and now tracks its upstream skill folder.
- 2026-09-15 · Created as a local directory marketplace with text-to-lottie.

## Upstream pin moves

