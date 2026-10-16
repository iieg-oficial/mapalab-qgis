#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZIP="$REPO_ROOT/dist/mapalab-qgis.zip"
IMAGEN="${SCAN_IMAGE:-python:3.12-slim}"
[ -f "$ZIP" ] || { echo "Falta $ZIP: corre make zip." >&2; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"

docker run --rm --network=host -v "$TMP:/scan:ro" "$IMAGEN" bash -c '
    set -e
    pip install -q --disable-pip-version-check --root-user-action=ignore \
        bandit detect-secrets flake8 >/dev/null
    cd /scan
    echo "  bandit"
    bandit -r mapalab -q -ll
    echo "  detect-secrets"
    detect-secrets scan --all-files mapalab | python3 -c "
import json, sys
hallazgos = json.load(sys.stdin)[\"results\"]
if hallazgos:
    print(json.dumps(hallazgos, indent=2))
    sys.exit(1)
"
    echo "  flake8 (informativo)"
    flake8 --max-line-length 100 mapalab || true
'
echo "  sin hallazgos que bloqueen la publicacion"
