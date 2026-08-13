#!/usr/bin/env bash
# Publish a News Flash HTML edition to the site.
#
#   ./publish.sh "BGAD News Flash 14 August 2026.html"          # deploys via railway up
#   ./publish.sh "BGAD News Flash 14 August 2026.html" --git     # commits and pushes instead
#
# The file is copied to public/issues/YYYY-MM-DD.html, dated today unless the
# filename contains a date it can parse.

set -euo pipefail
cd "$(dirname "$0")"

SRC="${1:-}"
MODE="${2:---railway}"

if [ -z "$SRC" ] || [ ! -f "$SRC" ]; then
  echo "usage: ./publish.sh <path to issue html> [--git|--railway]" >&2
  exit 1
fi

# Try to read a date like "14 August 2026" out of the filename, else use today.
STAMP=$(python3 - "$SRC" <<'PY'
import re, sys, datetime
name = sys.argv[1]
m = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', name)
if m:
    try:
        d = datetime.datetime.strptime(' '.join(m.groups()), '%d %B %Y').date()
        print(d.isoformat()); raise SystemExit
    except ValueError:
        pass
print(datetime.date.today().isoformat())
PY
)

mkdir -p public/issues
cp "$SRC" "public/issues/$STAMP.html"
echo "staged public/issues/$STAMP.html"

if [ "$MODE" = "--git" ]; then
  git add "public/issues/$STAMP.html"
  git commit -m "News Flash $STAMP"
  git push
  echo "pushed. Railway will redeploy from the connected repo."
else
  railway up
  echo "deployed."
fi

echo
echo "Flip this URL:"
echo "  https://<your-domain>/issues/$STAMP.html"
