#!/usr/bin/env bash
# Run the three blind judges in parallel, each read-only inside its own pack. CLI logins only:
# every *_API_KEY variable is removed from the environment first.
# usage: run_judges.sh <workdir>   (expects <workdir>/packs/{claude,grok,codex} and <workdir>/judge-prompt.md)
set -u
S="$(cd "$1" && pwd)"
OUT="$S/judges"; mkdir -p "$OUT"; : > "$OUT/status"
NOKEYS=(env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u XAI_API_KEY -u GROK_API_KEY -u CODEX_API_KEY -u GEMINI_API_KEY)
PROMPT="$(cat "$S/judge-prompt.md")"

( cd "$S/packs/claude" && "${NOKEYS[@]}" timeout 3000 claude -p "$PROMPT" --model opus \
    --allowedTools "Read,Glob,Grep" --disallowedTools "Bash,Write,Edit,NotebookEdit,WebFetch,WebSearch,Agent,Task" \
    --output-format text > "$OUT/claude.md" 2> "$OUT/claude.err"; echo "claude exit $?" >> "$OUT/status" ) &

( cd "$S/packs/grok" && "${NOKEYS[@]}" timeout 3000 grok -p "$PROMPT" --tools "read_file,list_dir,grep" \
    --no-subagents --disable-web-search --max-turns 150 --output-format plain > "$OUT/grok.md" 2> "$OUT/grok.err"; echo "grok exit $?" >> "$OUT/status" ) &

( "${NOKEYS[@]}" timeout 3000 codex exec -s read-only -C "$S/packs/codex" --skip-git-repo-check --ephemeral \
    -o "$OUT/codex.md" "$PROMPT" > "$OUT/codex.log" 2>&1; echo "codex exit $?" >> "$OUT/status" ) &

wait
cat "$OUT/status"
