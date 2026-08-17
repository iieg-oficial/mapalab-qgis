#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"
VERSION=$(grep '^version=' "$REPO_ROOT/metadata.txt" | cut -d= -f2)
NOMBRE="mapalab-qgis-$VERSION.zip"

rm -rf "$DIST_DIR/mapalab" "$DIST_DIR/$NOMBRE"
mkdir -p "$DIST_DIR/mapalab"

while read -r archivo; do
    mkdir -p "$DIST_DIR/mapalab/$(dirname "$archivo")"
    cp "$REPO_ROOT/$archivo" "$DIST_DIR/mapalab/$archivo"
done < <("$REPO_ROOT/scripts/plugin-files.sh")

cp "$REPO_ROOT/LICENSE" "$DIST_DIR/mapalab/LICENSE"

cd "$DIST_DIR"
zip -qr "$NOMBRE" mapalab
rm -rf "$DIST_DIR/mapalab"
cp "$NOMBRE" mapalab-qgis.zip

echo "$DIST_DIR/$NOMBRE"
