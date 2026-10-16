#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="$REPO_ROOT/theme.qss"
ENCABEZADO='/* Generado desde el manual de identidad. No editar a mano. */'

if [ -n "$1" ]; then
    ORIGEN="$1"
elif [ -n "$TOKENS_URL" ]; then
    ORIGEN=$(mktemp)
    trap 'rm -f "$ORIGEN"' EXIT
    if [ -n "$TOKENS_AUTH" ]; then
        curl -fsS -H "Authorization: Bearer $TOKENS_AUTH" "$TOKENS_URL" -o "$ORIGEN"
    else
        curl -fsS "$TOKENS_URL" -o "$ORIGEN"
    fi
else
    echo "Falta la ruta a un tokens.qss o TOKENS_URL." >&2
    echo "  make tokens ARCHIVO=~/Descargas/tokens.qss" >&2
    echo "  TOKENS_URL=<url del tokens.qss> TOKENS_AUTH=<token> make tokens" >&2
    exit 1
fi

if ! grep -q 'brandRole' "$ORIGEN"; then
    echo "El archivo no trae los roles de la identidad (brandRole): no es un tokens.qss." >&2
    exit 1
fi

{ echo "$ENCABEZADO"; sed '1{/^\/\*.*\*\/$/d}' "$ORIGEN"; } > "$DESTINO.tmp"
mv "$DESTINO.tmp" "$DESTINO"
echo "theme.qss actualizado"
