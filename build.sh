#!/bin/zsh
# Builds "dist/Call Switcher.app", signs it ad-hoc and packs a DMG.
# Uses the Python from .python-version; PYTHON_VERSION may override it with a version or an
# interpreter path (Homebrew or python.org).
set -euo pipefail
cd "${0:A:h}"

APP="dist/Call Switcher.app"

sync_args=(--locked)
[[ -n "${PYTHON_VERSION:-}" ]] && sync_args+=(--python "$PYTHON_VERSION")
uv sync "${sync_args[@]}"

rm -rf build dist
.venv/bin/python setup.py py2app

codesign --force --deep --sign - "$APP"
codesign --verify --verbose "$APP"

VERSION=$(.venv/bin/python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
DMG="dist/CallSwitcher-$VERSION-$(uname -m).dmg"

# DMG with the app and a link to /Applications for drag-and-drop installation.
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
hdiutil create -volname "Call Switcher" -srcfolder "$STAGING" -ov -format UDZO "$DMG"

echo "Fertig: $APP und $DMG"
