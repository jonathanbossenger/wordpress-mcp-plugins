#!/usr/bin/env bash
# Create one clean WordPress Studio site per shortlisted plugin, install + activate the plugin,
# seed a little content, then stop the site so 36 sites are not running at once.
#
# Usage:
#   ./setup_test_sites.sh setup  [slug ...]   create + install (default: every slug in shortlist_slugs.txt)
#   ./setup_test_sites.sh start  <slug>       start a site and print its URL and login
#   ./setup_test_sites.sh stop   [slug|--all] stop one site, or all Studio sites
#   ./setup_test_sites.sh status [slug ...]   show plugin + site status
#   ./setup_test_sites.sh delete <slug ...>   delete the site and its files (asks first; --yes to skip)
#
# Env overrides:
#   MCP_TEST_ROOT            where sites live          (default ~/Studio/mcp-tests)
#   MCP_TEST_ADMIN_PASSWORD  admin password            (default "password": local throwaway sites only)
#   MCP_TEST_KEEP_RUNNING=1  leave sites running after setup
#
# Results of each setup run are appended to setup_results.tsv.

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${MCP_TEST_ROOT:-$HOME/Studio/mcp-tests}"
SLUGS_FILE="$HERE/shortlist_slugs.txt"
RESULTS="$HERE/setup_results.tsv"
ADMIN_USER="admin"
ADMIN_PASSWORD="${MCP_TEST_ADMIN_PASSWORD:-password}"

site_path() { echo "$ROOT/$1"; }
wp() { local p="$1"; shift; studio wp --path "$p" "$@"; }

all_slugs() { grep -v '^\s*$' "$SLUGS_FILE"; }

log_result() { # slug status version note
  [ -f "$RESULTS" ] || printf 'timestamp\tslug\tstatus\tversion\tnote\n' > "$RESULTS"
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date -Iseconds)" "$1" "$2" "$3" "$4" >> "$RESULTS"
}

site_url() { # slug -> url from studio status json
  studio status --path "$(site_path "$1")" --format json 2>/dev/null | grep -o '"siteUrl": *"[^"]*"' | head -1 | sed 's/.*: *"\(.*\)"/\1/; s#/$##'
}

setup_one() {
  local slug="$1" path; path="$(site_path "$slug")"
  echo "=== $slug"
  if [ -e "$path" ]; then
    echo "  site folder exists, skipping (delete it first to start clean)"; log_result "$slug" skipped "" "site folder already exists"; return
  fi
  mkdir -p "$ROOT"
  if ! studio create --name "mcp-$slug" --path "$path" --skip-browser --skip-log-details \
        --admin-username "$ADMIN_USER" --admin-password "$ADMIN_PASSWORD" >/dev/null 2>&1; then
    echo "  FAILED to create site"; log_result "$slug" create-failed "" ""; return
  fi
  # Pretty permalinks (REST routes and many MCP endpoints need them) and some content for the task set
  wp "$path" rewrite structure '/%postname%/' --hard >/dev/null 2>&1
  wp "$path" option update blogdescription "Just another MCP test site" >/dev/null 2>&1
  wp "$path" post generate --count=8 --post_status=publish >/dev/null 2>&1

  local out status=ok note=""
  # Install first, then any dependencies from the "Requires Plugins" header, then activate
  local deps
  if ! out="$(wp "$path" plugin install "$slug" 2>&1)"; then
    status=install-failed; note="$(echo "$out" | tail -1)"
  else
    deps="$(wp "$path" plugin get "$slug" --field=requires_plugins 2>/dev/null | tail -1 | tr ',' ' ')"
    for d in $deps; do
      wp "$path" plugin install "$d" --activate >/dev/null 2>&1 || note="dependency $d failed"
    done
    [ -n "$deps" ] && note="${note:-deps: $deps}"
    out="$(wp "$path" plugin activate "$slug" 2>&1)"
  fi
  if [ "$status" = ok ] && ! wp "$path" plugin is-active "$slug" >/dev/null 2>&1; then
    status=not-active; note="$(echo "$out" | tail -1)"
  fi
  local version; version="$(wp "$path" plugin get "$slug" --field=version 2>/dev/null | tail -1)"
  echo "  $status ${version:+(v$version)} ${note:+- $note}"
  log_result "$slug" "$status" "$version" "$note"
  [ "${MCP_TEST_KEEP_RUNNING:-0}" = 1 ] || studio stop --path "$path" >/dev/null 2>&1
}

cmd="${1:-}"; shift || true
case "$cmd" in
  setup)
    command -v studio >/dev/null || { echo "studio CLI not found"; exit 1; }
    if [ $# -gt 0 ]; then slugs=("$@"); else slugs=($(all_slugs)); fi
    for s in "${slugs[@]}"; do setup_one "$s"; done
    echo "Done. Results: $RESULTS"
    ;;
  start)
    [ $# -eq 1 ] || { echo "usage: $0 start <slug>"; exit 1; }
    studio start --path "$(site_path "$1")" --skip-browser >/dev/null 2>&1
    echo "URL:      $(site_url "$1")"
    echo "Admin:    $(site_url "$1")/wp-admin   ($ADMIN_USER / $ADMIN_PASSWORD)"
    ;;
  stop)
    if [ "${1:-}" = "--all" ] || [ $# -eq 0 ]; then studio stop --all; else studio stop --path "$(site_path "$1")"; fi
    ;;
  status)
    if [ $# -gt 0 ]; then slugs=("$@"); else slugs=($(all_slugs)); fi
    for s in "${slugs[@]}"; do
      p="$(site_path "$s")"
      [ -e "$p" ] && printf '%-48s exists\n' "$s" || printf '%-48s not created\n' "$s"
    done
    echo; studio list
    ;;
  delete)
    yes=0; [ "${1:-}" = "--yes" ] && { yes=1; shift; }
    [ $# -gt 0 ] || { echo "usage: $0 delete [--yes] <slug ...>"; exit 1; }
    for s in "$@"; do
      p="$(site_path "$s")"
      [ -e "$p" ] || { echo "$s: no site at $p"; continue; }
      if [ $yes -eq 0 ]; then read -r -p "Delete site and files at $p? [y/N] " a; [ "$a" = y ] || continue; fi
      studio delete --path "$p" && echo "$s: deleted"
    done
    ;;
  *)
    sed -n '2,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1
    ;;
esac
