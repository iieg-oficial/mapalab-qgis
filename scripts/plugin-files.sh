#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXCLUIDOS='^(scripts/|docs/|make/|\.githooks/|\.github/|Makefile|README\.md|LICENSE|\.gitignore)'

git -C "$REPO_ROOT" ls-files | grep -vE "$EXCLUIDOS" | sort
