# Changelog

The scheduled pin job writes one line per upstream change under "Upstream pin moves", newest first. Entries above it are changes to what this marketplace carries.

## Marketplace changes

- 2026-10-08 · Each entry now names the one skill it loads; the ten `git-subdir` entries point at the folder that holds their skill, the form Anthropic's own marketplaces use, and unlazy stays a `url` source at its repository root. The pin job checks each plugin before moving it (skills only, within limits, forward only), handles each plugin on its own, honours holds in `holds.json`, flags upstreams that start publishing their own marketplace, keeps its schedule alive past GitHub's 60-day limit, and checks hand edits on push.
- 2026-10-08 · Added verify-all-runtime-sinks, the MiniMax companion to cross-layer-drift-sweep, so the uploaded account copy can go.
- 2026-10-08 · Added design-qa (OpenAI's Product Design helper, from openai/plugins, where OpenAI now publishes it after resetting openai/role-specific-plugins) and visual-verdict (the single skill from vibeeval/vibecosystem, without the rest of that bundle).
- 2026-10-05 · Moved from a local directory on the docked Mac to this repository, so Claude Code, Codex and claude.ai can all subscribe to it. Added no-ai-slop, unlazy, cross-layer-drift-sweep, database-lookup, scientific-critical-thinking, figma-generate-project-plan and figma-video-interaction-mapper. text-to-lottie lost its fixed "1.0.0" version and now tracks its upstream skill folder.
- 2026-09-15 · Created as a local directory marketplace with text-to-lottie.

## Upstream pin moves

