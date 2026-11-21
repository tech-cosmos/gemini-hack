#!/usr/bin/env bash
# Shared helpers for the kit scripts. Use: . "$(dirname "$0")/lib.sh"
# No `set -e` here: some callers are Claude Code hooks and must always exit 0.
# Written for bash 3.2 (macOS) and Git Bash (Windows): no arrays of arrays, no GNU-only flags.

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KIT_ROOT" || exit 0
# shellcheck disable=SC1091
[ -f kit.env ] && . ./kit.env

kit_lc() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

# owner/name of the team repo
kit_repo() {
  if [ -n "${KIT_REPO:-}" ]; then echo "$KIT_REPO"; return; fi
  git remote get-url origin 2>/dev/null \
    | sed -E 's#^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)##; s#\.git$##'
}

kit_lead() {
  if [ -n "${KIT_LEAD:-}" ]; then echo "$KIT_LEAD"; else kit_repo | cut -d/ -f1; fi
}

# Your GitHub login. Cached in .git so the per-message hook stays fast; scripts/catchup refreshes it.
kit_me() {
  local f me
  f="$(git rev-parse --git-common-dir 2>/dev/null)/kit-me"
  if [ -s "$f" ]; then cat "$f"; return 0; fi
  me=$(gh api user --jq .login 2>/dev/null) || return 1
  [ -n "$me" ] || return 1
  echo "$me" > "$f" 2>/dev/null
  echo "$me"
}
kit_me_refresh() { rm -f "$(git rev-parse --git-common-dir 2>/dev/null)/kit-me" 2>/dev/null; kit_me; }

kit_is_lead() {
  local me; me=$(kit_me) || return 1
  [ "$(kit_lc "$me")" = "$(kit_lc "$(kit_lead)")" ]
}

# ---- clock ---------------------------------------------------------------
# "YYYY-MM-DDTHH:MM" (local time) -> epoch seconds
kit_epoch() {
  if date --version >/dev/null 2>&1; then date -d "$1" +%s 2>/dev/null
  else date -j -f "%Y-%m-%dT%H:%M:%S" "$1:00" +%s 2>/dev/null; fi
}
# epoch -> HH:MM
kit_hm() {
  if date --version >/dev/null 2>&1; then date -d "@$1" +%H:%M; else date -r "$1" +%H:%M; fi
}
kit_fmt_min() {
  local m=$1
  if [ "$m" -ge 60 ]; then echo "$((m / 60)) h $((m % 60)) min"; else echo "$m min"; fi
}
# Prints "<percent of window used> <minutes left>"; fails when the clock is not set.
kit_progress() {
  [ -n "${KIT_START:-}" ] && [ -n "${KIT_DEADLINE:-}" ] || return 1
  local s d n
  s=$(kit_epoch "$KIT_START") && d=$(kit_epoch "$KIT_DEADLINE") || return 1
  [ -n "$s" ] && [ -n "$d" ] && [ "$d" -gt "$s" ] || return 1
  n=$(date +%s)
  echo "$(( (n - s) * 100 / (d - s) )) $(( (d - n) / 60 ))"
}
# Lines "percent|text"
kit_gates() { printf '%s\n' "${KIT_GATES:-}" | grep -E '^[0-9]+\|'; }
# percent -> HH:MM of that gate
kit_gate_time() {
  local s d
  s=$(kit_epoch "$KIT_START"); d=$(kit_epoch "$KIT_DEADLINE")
  kit_hm $(( s + (d - s) * $1 / 100 ))
}
kit_clock_line() {
  local p pct left next
  p=$(kit_progress) || { echo "⏱ no clock yet: set KIT_START and KIT_DEADLINE in kit.env (scripts/init does it)"; return; }
  pct=${p% *}; left=${p#* }
  if [ "$pct" -lt 0 ]; then echo "⏱ $(date +%H:%M) · building starts at $(kit_hm "$(kit_epoch "$KIT_START")")"; return; fi
  if [ "$left" -lt 0 ]; then echo "⏱ $(date +%H:%M) · DEADLINE PASSED $(kit_fmt_min $(( -left ))) ago"; return; fi
  next=$(kit_gates | while IFS='|' read -r g t; do
    if [ "$g" -gt "$pct" ]; then echo "$(kit_gate_time "$g") · $t"; break; fi
  done)
  echo "⏱ $(date +%H:%M) · $(kit_fmt_min "$left") left (deadline $(kit_hm "$(kit_epoch "$KIT_DEADLINE")")) · ${pct}% of the window used${next:+
   next gate $next}"
}

# ---- submission facts ----------------------------------------------------
# Names of the rows in docs/SUBMISSION.md whose value is still empty, comma separated.
kit_submission_missing() {
  [ -f docs/SUBMISSION.md ] || return 0
  awk -F'|' '/^\|/ {
      n=$2; v=$3
      gsub(/^[ \t*]+|[ \t*]+$/, "", n); gsub(/^[ \t]+|[ \t]+$/, "", v)
      if (n == "" || n == "Fact" || n ~ /^[-: ]+$/) next
      if (v == "") m = m (m ? ", " : "") n
    } END { if (m) print m }' docs/SUBMISSION.md
}

# ---- directives ----------------------------------------------------------
# One line per open directive that is for you: assigned to you, or labeled `everyone` and you
# have not commented "done". The lead also gets one "⚠" line per directive nobody acked in time.
kit_directive_lines() {
  local repo me lead prog
  repo=$(kit_repo); me=$(kit_lc "$(kit_me)")
  [ -n "$repo" ] && [ -n "$me" ] || return 0
  if kit_is_lead; then lead=true; else lead=false; fi
  # shellcheck disable=SC2016
  prog='
    def age: ((now - (.createdAt | fromdateiso8601)) / 60 | floor);
    [ .[] | { n: .number,
              t: (.title | sub("^DIRECTIVE: *"; "")),
              age: age,
              to: [.assignees[].login | ascii_downcase],
              all: ([.labels[].name] | index("everyone") != null),
              by: [.comments[] | {who: (.author.login | ascii_downcase), body: (.body | ascii_downcase)}] } ] as $d
    | ( $d[] | . as $x
        | [$x.by[] | select(.who == "__ME__")] as $mine
        | select( ($x.to | index("__ME__") != null)
                  or ($x.all and ([$mine[] | .body | test("^\\s*done")] | any | not)) )
        | "#\($x.n) \($x.t)" + (if ($mine | length) == 0 then "   <- not acked: scripts/ack \($x.n)" else "" end) ),
      ( if __LEAD__ then
          ( $d[] | . as $x | select($x.age >= __ACK__)
            | ($x.to - [$x.by[].who]) as $silent | select(($silent | length) > 0)
            | "⚠ #\($x.n) no ack from \($silent | join(", ")) after \($x.age) min: \($x.t)" )
        else empty end )'
  prog=${prog//__ME__/$me}; prog=${prog//__LEAD__/$lead}; prog=${prog//__ACK__/${KIT_ACK_MIN:-10}}
  gh issue list --repo "$repo" --label directive --state open --limit 50 \
    --json number,title,assignees,labels,comments,createdAt --jq "$prog" 2>/dev/null
}

# ---- small tools ---------------------------------------------------------
# In-place sed that works on macOS and Linux and keeps the file mode.
kit_sub() {
  local f=$1 t; shift
  t=$(mktemp) || return 1
  sed -E "$@" "$f" > "$t" && cat "$t" > "$f"
  rm -f "$t"
}
# Desktop notification for the human (macOS only; silent elsewhere).
kit_notify() {
  [ "${KIT_NOTIFY:-1}" = "1" ] || return 0
  command -v osascript >/dev/null 2>&1 || return 0
  local m; m=$(printf '%s' "$1" | tr -d '"\\' | cut -c1-200)
  osascript -e "display notification \"$m\" with title \"${KIT_EVENT:-Hackathon}\" sound name \"Glass\"" >/dev/null 2>&1 || true
}
