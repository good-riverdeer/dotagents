#!/bin/sh
# robbyrussell-style status line: ➜  dir git:(branch) ✗  [model ctx%]
in=$(cat)
cwd=$(printf '%s' "$in" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(printf '%s' "$in" | jq -r '.model.display_name // empty')
pct=$(printf '%s' "$in" | jq -r '.context_window.used_percentage // empty' | cut -d. -f1)

out="\033[1;32m➜\033[0m  \033[36m$(basename "${cwd:-$PWD}")\033[0m"
if b=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null); then
  out="$out \033[1;34mgit:(\033[31m$b\033[34m)\033[0m"
  [ -n "$(git -C "$cwd" status --porcelain 2>/dev/null | head -1)" ] && out="$out \033[33m✗\033[0m"
fi
[ -n "$model" ] && out="$out  \033[2m[$model${pct:+ ${pct}%%}]\033[0m"
printf "$out"
