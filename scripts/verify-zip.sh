#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZIP="$REPO_ROOT/dist/mapalab-qgis.zip"
EXCLUIDOS='^(scripts/|docs/|Makefile|README\.md|LICENSE|\.gitignore|\.githooks/|make/)'

[ -f "$ZIP" ] || { echo "Falta $ZIP: corre make zip." >&2; exit 1; }

if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
    echo "El repositorio tiene cambios sin commitear: el zip no representaría un commit." >&2
    exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"

git -C "$REPO_ROOT" ls-files | grep -vE "$EXCLUIDOS" | sort > "$TMP/esperados.txt"
(cd "$TMP/mapalab" && find . -type f ! -name LICENSE | sed 's|^\./||' | sort) > "$TMP/incluidos.txt"

if ! diff -q "$TMP/esperados.txt" "$TMP/incluidos.txt" >/dev/null; then
    echo "El zip no coincide con el repositorio:" >&2
    diff "$TMP/esperados.txt" "$TMP/incluidos.txt" >&2 || true
    exit 1
fi

DIFERENTES=0
while read -r archivo; do
    cmp -s "$REPO_ROOT/$archivo" "$TMP/mapalab/$archivo" || {
        echo "  contenido distinto: $archivo" >&2
        DIFERENTES=1
    }
done < "$TMP/esperados.txt"
[ "$DIFERENTES" -eq 0 ] || exit 1

echo "  $(wc -l < "$TMP/esperados.txt") archivos, idénticos al commit $(git -C "$REPO_ROOT" rev-parse --short HEAD)"
