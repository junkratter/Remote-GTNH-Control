#!/usr/bin/env bash
# Sync this monorepo into a public fork working tree without private overlays.
#
# Usage:
#   ./tools/sync-public-fork.sh [SOURCE_DIR] [DEST_DIR]
# Defaults: SOURCE = repo root, DEST = ~/Documents/GitHub/Remote-GTNH-Control
#
# Excludes: .git, build artifacts, server/.env, real oc-client/env.lua,
#           private .cursor/rules/server.mdc (replaced from server.mdc.example).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${1:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DST="${2:-$HOME/Documents/GitHub/Remote-GTNH-Control}"

if [[ ! -d "$DST" ]]; then
  echo "Destination directory missing: $DST" >&2
  exit 1
fi

RSYNC_EXCLUDES=(
  --exclude='.git/'
  --exclude='node_modules/'
  --exclude='dist/'
  --exclude='.venv/'
  --exclude='__pycache__/'
  --exclude='*.pyc'
  --exclude='.pytest_cache/'
  --exclude='htmlcov/'
  --exclude='.coverage'
  --exclude='*.egg-info/'
  --exclude='server/.env'
  --exclude='oc-client/env.lua'
  --exclude='.cursor/rules/server.mdc'
)

rsync -a "${RSYNC_EXCLUDES[@]}" "$SRC/" "$DST/"

if [[ -f "$SRC/.cursor/rules/server.mdc.example" ]]; then
  mkdir -p "$DST/.cursor/rules"
  cp "$SRC/.cursor/rules/server.mdc.example" "$DST/.cursor/rules/server.mdc"
fi

if [[ -f "$SRC/oc-client/env.lua.example" ]]; then
  cp "$SRC/oc-client/env.lua.example" "$DST/oc-client/env.lua"
fi

# Replace host-specific strings in the public tree only (local source unchanged).
sanitize_public() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  if grep -qE 'junkratter|85\.193\.65\.88' "$f" 2>/dev/null; then
    sed -i '' \
      -e 's/85\.193\.65\.88/YOUR_PUBLIC_IP/g' \
      -e 's/api\.gtnh\.junkratter12\.ru/api.gtnh.example.com/g' \
      -e 's/gtnh\.junkratter12\.ru/gtnh.example.com/g' \
      "$f"
  fi
}

while IFS= read -r -d '' f; do
  sanitize_public "$f"
done < <(find "$DST" -type f \( -name '*.md' -o -name '*.conf' -o -name 'README*' \) -print0 2>/dev/null)

echo "Synced $SRC -> $DST"
echo "Note: review kb/ and tools/deploy for any host-specific lines before git push."
