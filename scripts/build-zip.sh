#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"
VERSION=$(grep '^version=' "$REPO_ROOT/metadata.txt" | cut -d= -f2)
NOMBRE="mapalab-qgis-$VERSION.zip"

rm -rf "$DIST_DIR/mapalab" "$DIST_DIR/$NOMBRE"
mkdir -p "$DIST_DIR/mapalab"

for archivo in $(git -C "$REPO_ROOT" ls-files); do
    case "$archivo" in
        scripts/*|docs/*|Makefile|README.md|LICENSE|.gitignore) continue ;;
    esac
    mkdir -p "$DIST_DIR/mapalab/$(dirname "$archivo")"
    cp "$REPO_ROOT/$archivo" "$DIST_DIR/mapalab/$archivo"
done

cp "$REPO_ROOT/LICENSE" "$DIST_DIR/mapalab/LICENSE"

cd "$DIST_DIR"
zip -qr "$NOMBRE" mapalab
rm -rf "$DIST_DIR/mapalab"
cp "$NOMBRE" mapalab-qgis.zip

echo "$DIST_DIR/$NOMBRE"
