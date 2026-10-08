#!/usr/bin/env bash
# Tell the repository owner that moved pins are waiting for claude.ai.
#
# claude.ai does not act on pushes to an account marketplace on its own
# (anthropics/claude-code#93825), so new pins reach claude.ai and Cowork only when
# someone selects Check for updates. After the pin job pushes moves, this keeps one
# open issue, assigned to the owner, and comments on it with the moves, so the owner
# is notified exactly when there is something to pull.
#
# Usage: ask_for_update.sh MOVES_FILE   (needs GH_TOKEN, GITHUB_REPOSITORY, GITHUB_REPOSITORY_OWNER)
# DRY_RUN=1 prints the requests instead of sending them.
set -euo pipefail

moves_file=$1
[ -s "$moves_file" ] || exit 0
repo=$GITHUB_REPOSITORY
owner=$GITHUB_REPOSITORY_OWNER
title="Upstream changes waiting for Check for updates on claude.ai"
steps="In claude.ai: Customize > Plugins > Add > Manage marketplaces > yz-personal > menu > Check for updates. Claude Code on the Mac updates on its own."
moves=$(cat "$moves_file")

send() {
  if [ "${DRY_RUN:-}" = 1 ]; then printf 'gh api'; printf ' %q' "$@"; printf '\n'; else gh api "$@" >/dev/null; fi
}

number=$(gh api "repos/$repo/issues?state=open&per_page=100" \
  --jq "[.[] | select(.pull_request == null and .title == \"$title\")][0].number // empty")

if [ -z "$number" ]; then
  body="@$owner These pins moved in yz-personal:

$moves

claude.ai does not yet pick up pushes to an account marketplace on its own ([anthropics/claude-code#93825](https://github.com/anthropics/claude-code/issues/93825)), so they reach claude.ai and Cowork when you select Check for updates. $steps

The pin job comments here each time pins move. Leave this issue open; closing it only means the next move opens a new one."
  send "repos/$repo/issues" -X POST -f "title=$title" -f "body=$body" -f "assignees[]=$owner"
else
  body="These pins moved:

$moves

$steps"
  send "repos/$repo/issues/$number/comments" -X POST -f "body=$body"
fi
