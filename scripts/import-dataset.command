#!/usr/bin/env bash
# One-click measurement dataset import for macOS — double-click this file.
#
# A Terminal window opens and asks for the dataset path (folder or .zip, anywhere
# on this Mac). It copies it into the running digitaltwins-api container
# (progress bar if `pv` is installed: `brew install pv`), then runs the importer.
# Sign in (admin or researcher) via your browser when prompted.
set -euo pipefail

if [ "$#" -ge 1 ] && [ "${1#-}" = "$1" ]; then
  SRC="$1"; shift
else
  read -r -p "Dataset folder or .zip (full path): " SRC
fi
SRC="${SRC%/}"
if [ ! -e "$SRC" ]; then
  echo "  ✗ No such path: $SRC"
  read -r -p "Press Enter to close…" _
  exit 1
fi

CID="$(docker ps -q --filter "label=com.docker.compose.service=digitaltwins-api" | head -n1)"
if [ -z "$CID" ]; then
  echo "  ✗ The digitaltwins-api container is not running."
  read -r -p "Press Enter to close…" _
  exit 1
fi

BASE="$(basename "$SRC")"
STAGE_DIR="/dataset_staging/import-staging"
STAGE="$STAGE_DIR/$BASE"

docker exec "$CID" sh -c "rm -rf '$STAGE'; mkdir -p '$STAGE_DIR'"

_src_bytes() {
  if du -sb "$1" >/dev/null 2>&1; then du -sb "$1" | cut -f1
  else du -sk "$1" | awk '{print $1*1024}'; fi
}

if command -v pv >/dev/null 2>&1 && docker exec "$CID" sh -c 'command -v tar >/dev/null 2>&1'; then
  echo "  Copying '$BASE' into the container…"
  tar -C "$(dirname "$SRC")" -cf - "$BASE" | pv -s "$(_src_bytes "$SRC")" | docker exec -i "$CID" tar -C "$STAGE_DIR" -xf -
else
  echo "  Copying '$BASE' ($(du -sh "$SRC" 2>/dev/null | cut -f1)) into the container… (brew install pv for a progress bar)"
  docker cp "$SRC" "$CID:$STAGE"
fi

set +e
docker exec -it "$CID" python -m digitaltwins.cli.import_dataset "$STAGE" --move "$@"
status=$?

echo
read -r -p "Done (exit $status). Press Enter to close…" _
exit $status
