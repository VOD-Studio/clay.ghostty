#!/usr/bin/env bash
# Print the ANSI palette and common terminal output with the current theme.
# Run inside Ghostty after selecting clay-dark or clay-light.
set -euo pipefail

esc=$'\033'
reset="${esc}[0m"
bold="${esc}[1m"
dim="${esc}[2m"
italic="${esc}[3m"
under="${esc}[4m"

fg() { printf '%s[%sm' "$esc" "$1"; }

names=(black red green yellow blue magenta cyan white)

section() { printf '\n%s%s%s\n' "$bold" "$1" "$reset"; }

section "ANSI 16"
for row in 0 1; do
  # Normal colors use SGR 30-37/40-47, bright colors 90-97/100-107.
  base=$((row == 0 ? 30 : 90))
  for i in 0 1 2 3 4 5 6 7; do
    printf '%s[%sm          %s ' "$esc" "$((base + 10 + i))" "$reset"
  done
  printf '\n'
  for i in 0 1 2 3 4 5 6 7; do
    printf '%s%-11s%s' "$(fg "$((base + i))")" "$((row * 8 + i)) ${names[i]}" "$reset"
  done
  printf '\n'
done

section "Text"
printf '%sdefault%s  %sbold%s  %sdim%s  %sitalic%s  %sunderline%s  %sreverse%s\n' \
  "" "" "$bold" "$reset" "$dim" "$reset" "$italic" "$reset" "$under" "$reset" "${esc}[7m" "$reset"

section "Prompt"
printf '%s~/Developer/clay.ghostty%s on %s master%s %s?1 !2%s\n' \
  "$(fg 34)$bold" "$reset" "$(fg 35)" "$reset" "$(fg 31)" "$reset"
printf '%s❯%s git status --short\n' "$(fg 32)$bold" "$reset"
printf '%sM%s  themes/clay-dark\n' "$(fg 32)" "$reset"
printf ' %sM%s themes/clay-light\n' "$(fg 31)" "$reset"
printf '%s??%s scripts/preview.sh\n' "$(fg 31)" "$reset"
printf '%s❯%s false\n' "$(fg 31)$bold" "$reset"

section "git diff"
printf '%sdiff --git a/themes/clay-dark b/themes/clay-dark%s\n' "$bold" "$reset"
printf '%sindex 4ed61d8..53ba1c6 100644%s\n' "$bold" "$reset"
printf '%s--- a/themes/clay-dark%s\n' "$bold" "$reset"
printf '%s+++ b/themes/clay-dark%s\n' "$bold" "$reset"
printf '%s@@ -14,4 +14,4 @@%s # 选区：bright 在 selection 上\n' "$(fg 36)" "$reset"
printf ' selection-background = #363636\n'
printf '%s-selection-foreground = #cccccc%s\n' "$(fg 31)" "$reset"
printf '%s+selection-foreground = #e6e6e6%s\n' "$(fg 32)" "$reset"

section "ls --color"
printf '%sdesign%s/  %sscripts%s/  %stests%s/  %sthemes%s/  ' \
  "$(fg 34)$bold" "$reset" "$(fg 34)$bold" "$reset" "$(fg 34)$bold" "$reset" "$(fg 34)$bold" "$reset"
printf '%spreview.sh%s*  %sclay -> themes%s@  Makefile  README.md  %sarchive.tar.gz%s\n' \
  "$(fg 32)$bold" "$reset" "$(fg 36)$bold" "$reset" "$(fg 31)$bold" "$reset"

section "Compiler"
printf '%serror[E0308]%s%s: mismatched types%s\n' "$(fg 31)$bold" "$reset" "$bold" "$reset"
printf '  %s-->%s src/main.rs:4:18\n' "$(fg 34)$bold" "$reset"
printf '   %s|%s\n' "$(fg 34)$bold" "$reset"
printf '%s4%s  %s|%s     let n: u32 = "clay";\n' "$(fg 34)$bold" "$reset" "$(fg 34)$bold" "$reset"
printf '   %s|%s                  %s^^^^^^ expected `u32`, found `&str`%s\n' \
  "$(fg 34)$bold" "$reset" "$(fg 31)$bold" "$reset"
printf '%swarning%s%s: unused variable: `palette`%s\n' "$(fg 33)$bold" "$reset" "$bold" "$reset"
printf '%snote%s: `#[warn(unused_variables)]` on by default\n' "$(fg 36)$bold" "$reset"

section "Logs"
printf '%s2026-11-12T10:23:01Z%s %sERROR%s request failed status=500\n' "$(fg 90)" "$reset" "$(fg 31)$bold" "$reset"
printf '%s2026-11-12T10:23:02Z%s %s WARN%s retrying in 2s\n' "$(fg 90)" "$reset" "$(fg 33)$bold" "$reset"
printf '%s2026-11-12T10:23:04Z%s %s INFO%s listening on :8080\n' "$(fg 90)" "$reset" "$(fg 32)" "$reset"
printf '%s2026-11-12T10:23:05Z%s %sDEBUG%s cache hit key=clay\n' "$(fg 90)" "$reset" "$(fg 34)" "$reset"
printf '%s2026-11-12T10:23:05Z%s %sTRACE%s %sspan closed%s\n' "$(fg 90)" "$reset" "$(fg 35)" "$reset" "$(fg 90)" "$reset"
printf '\n'
