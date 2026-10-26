#!/bin/sh
# Builds the Flatpak and packs it as "dist/CallSwitcher-<version>-<arch>.flatpak".
# Needs flatpak-builder (or the org.flatpak.Builder Flatpak) and the Flathub remote; the KDE
# runtime and the PySide6 BaseApp are installed from Flathub (per user) if they are missing.
set -eu
cd "$(dirname "$0")"

APP_ID=org.phonixpbx.callswitcher
VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
ARCH=$(flatpak --default-arch)

if command -v flatpak-builder >/dev/null; then
    set -- flatpak-builder
else
    set -- flatpak run --filesystem="$PWD" org.flatpak.Builder
fi

rm -rf build/flatpak build/flatpak-repo
"$@" --user --install-deps-from=flathub --force-clean --repo=build/flatpak-repo \
    build/flatpak "packaging/linux/$APP_ID.yml"

mkdir -p dist
BUNDLE="dist/CallSwitcher-$VERSION-$ARCH.flatpak"
flatpak build-bundle --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    build/flatpak-repo "$BUNDLE" "$APP_ID"

echo "Done: $BUNDLE"
