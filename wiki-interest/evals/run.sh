#!/usr/bin/env bash
# Run one eval case through Claude Code with this skill installed in a fresh workspace.
# Usage:  bash evals/run.sh <case-id> "<prompt>" [--resume <session-id>]
#         bash evals/run.sh <case-id> @prompt.txt [--resume <session-id>]
# The @file form avoids quoting prompts that contain apostrophes or non-Latin text.
# Env:    CLAUDE_BIN (default: claude)  MODEL (default: claude-haiku-4-5)
#         OUT (default: ${TMPDIR:-/tmp}/wiki-interest-evals)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASE="$1"; PROMPT="$2"; shift 2
[ "${PROMPT#@}" != "$PROMPT" ] && PROMPT="$(cat "${PROMPT#@}")"
OUT="${OUT:-${TMPDIR:-/tmp}/wiki-interest-evals}"
WS="$OUT/$CASE"

mkdir -p "$WS/.claude/skills"
ln -sfn "$SKILL_DIR" "$WS/.claude/skills/wiki-interest"
cd "$WS"

"${CLAUDE_BIN:-claude}" -p "$PROMPT" "$@" \
  --model "${MODEL:-claude-haiku-4-5}" \
  --output-format stream-json --verbose \
  --allowedTools "Bash,Read,Write,Edit,Skill,Glob,Grep" \
  > "transcript-$(date +%H%M%S).jsonl"

python3 "$SKILL_DIR/evals/summarize.py" "$(ls -t transcript-*.jsonl | head -1)"
