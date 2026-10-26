<img src="assets/icon.png" width="128" alt="Call Switcher icon">

# Call Switcher

A menu bar app for macOS and a tray app for Linux and Windows that handles `tel:`, `callto:` and `sip:` links. It places the call
through a phone app (such as Telephone.app), the click-to-call API of
[PhonixPBX](https://github.com/PhonixPBX/PhonixPBX), or Asterisk ARI (originate).

Runs on macOS 26 and 27 (Apple Silicon), on Linux as a Flatpak (see [Linux](#linux)) and on
Windows 10 and 11 (see [Windows](#windows)). Available in English, German, French, Italian,
Spanish and Portuguese (Brazil). The app follows the language order in System Settings →
General → Language & Region and falls back to English.

## Installation

1. Download the DMG from [Releases](https://github.com/PhonixPBX/Call-Switcher/releases),
   open it and drag "Call Switcher" onto the "Applications" folder.
2. Open the app. The first time, macOS blocks it; see
   [Opening the app the first time](#opening-the-app-the-first-time).
3. A phone icon appears in the menu bar. Choose **Settings…**
4. Pick a method at the top, set it up and turn it on with **Enabled**. All three can be
   configured; only the enabled ones are used (marked with ✓):
   - **Phone App**: choose the app, for example `/Applications/Telephone.app`.
   - **PhonixPBX**: enter the server URL (for example `https://pbx.example.com`), your own
     extension and an API token, then click **Test Connection**. For a self-signed
     certificate, turn on "Don’t verify certificate".
   - **Asterisk ARI**: enter host, port, user, password, endpoint (your own phone, for
     example `PJSIP/100`) and context, then click **Test Connection**.
5. Click **Set as Default** so that `tel:` links open in Call Switcher.

If more than one method is enabled, Call Switcher asks which one to use for every `tel:`
link. If only one is enabled, it dials right away.

The ARI password and the Phonix token are stored in the keychain (service
`org.phonixpbx.callswitcher`, accounts `ari` and `phonix`).

### Opening the app the first time

Call Switcher is signed ad hoc but not notarized by Apple, so macOS refuses to open it after
it was downloaded and says it "could not verify" the app. The app is not damaged. Since
macOS 15, right-click → Open no longer gets around this. Do this once:

1. Open the app. When macOS shows the warning, click **Done**, not **Move to Trash**.
2. Open System Settings → Privacy & Security and scroll down. Next to the message about
   "Call Switcher", click **Open Anyway** and confirm with your password or Touch ID.
3. Open the app again and click **Open**. macOS does not ask again after that.

The **Open Anyway** button only shows up for about an hour after the blocked attempt. If it
is missing, open the app again first.

Alternatively, remove the download flag in Terminal, then open the app normally:

```sh
xattr -dr com.apple.quarantine "/Applications/Call Switcher.app"
```

If macOS already refuses to open the DMG, do the same for the DMG, for example
`xattr -d com.apple.quarantine ~/Downloads/CallSwitcher-*.dmg`.

## Linux

1. Download `CallSwitcher-<version>-x86_64.flatpak` from
   [Releases](https://github.com/PhonixPBX/Call-Switcher/releases) and install it:

   ```sh
   flatpak install --user CallSwitcher-*.flatpak
   ```

   The KDE runtime and PySide6 come from Flathub; add it first if needed:
   `flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo`.
2. Open "Call Switcher" from the app menu. The settings window opens; set up the methods as
   on macOS and click **Set as Default** so that `tel:` links open in Call Switcher.
3. **Phone App** lists the installed apps that handle `sip:`, `tel:` or `callto:` links, such
   as Linphone. Call Switcher starts the chosen app with the link.

The tray icon works on KDE Plasma, Xfce, Cinnamon and other desktops with StatusNotifierItem
support. GNOME needs the
[AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/);
without it there is no tray icon, but `tel:` links still work and starting the app from the
app menu opens the settings.

The ARI password and the Phonix token are stored in the Secret Service (GNOME keyring or
KWallet) under service `org.phonixpbx.callswitcher`, accounts `ari` and `phonix`. The other
settings are in `~/.var/app/org.phonixpbx.callswitcher/config/call-switcher/settings.json`.

The Flatpak may run commands on the host (`--talk-name=org.freedesktop.Flatpak`). It needs this
to list and start the phone app and to set the default handler for `tel:` links with
`xdg-mime`.

## Windows

1. Download `CallSwitcher-<version>-x64-setup.exe` from
   [Releases](https://github.com/PhonixPBX/Call-Switcher/releases) and run it. It installs for
   the current user, without admin rights.
2. The installer is not signed, so Windows SmartScreen warns about it the first time. Click
   **More info**, then **Run anyway**.
3. Call Switcher starts with a phone icon in the notification area (it may be hidden behind
   the arrow). Right-click it and choose **Settings…**; set up the methods as on macOS.
4. Click **Set as Default**. Windows does not let apps make themselves the default, so this
   opens Settings → Apps → Default apps → Call Switcher; choose Call Switcher there for `TEL`,
   `CALLTO` and `SIP`.
5. **Phone App** lists the installed apps that handle `sip:`, `tel:` or `callto:` links, such
   as MicroSIP. Call Switcher starts the chosen app with the link.

The ARI password and the Phonix token are stored in the Windows Credential Manager under
`org.phonixpbx.callswitcher`, accounts `ari` and `phonix`. The other settings are in
`%APPDATA%\Call Switcher\settings.json`. "Start at login" writes the `Call Switcher` value
under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. Uninstall Call Switcher under
Settings → Apps.

## PhonixPBX

Call Switcher uses `POST /api/v1/calls`: your phone rings first, and once you answer,
Phonix dials the number with that phone's outgoing rules and caller ID.

Each user needs their own API token with the *May place calls* option (under
*Advanced → API tokens*, or `phonix token create --allow-calls`). A read-only token with
this option is enough and cannot change the configuration. **Test Connection** checks the
token, the call permission and the extension without placing a call.

## Asterisk ARI

For your own Asterisk server with ARI. PhonixPBX turns ARI off, so use the PhonixPBX method
there.

`ari.conf` needs a user and `http.conf` must be enabled. When originating, the configured
endpoint rings first; once answered, Asterisk dials the number in the given context.

## Development

Requires [uv](https://docs.astral.sh/uv/) (`brew install uv`).

### macOS

```sh
./build.sh
```

The script builds `dist/Call Switcher.app` (ad-hoc signed) and
`dist/CallSwitcher-<version>-arm64.dmg`. It uses the Python version from `.python-version`
(3.14); `PYTHON_VERSION=… ./build.sh` overrides it with a version or an interpreter path.
py2app needs a framework build of Python (Homebrew or python.org), so `pyproject.toml` tells
uv to use only installed interpreters and never download its own. Python 3.15 does not work
yet: py2app 0.28 misses new standard library modules and the app fails to launch.

Dependabot keeps the Python packages and GitHub Actions up to date.

### Linux

The Linux app uses Qt (PySide6) and runs on the system Python (3.12 or newer); pass it to
uv if it differs from `.python-version`:

```sh
uv sync --python /usr/bin/python3
uv run python -m call_switcher
```

```sh
./build-linux.sh
```

The script builds the Flatpak with `flatpak-builder` (or the `org.flatpak.Builder` Flatpak)
and packs it as `dist/CallSwitcher-<version>-<arch>.flatpak`. The manifest and the desktop
integration are in [packaging/linux/](packaging/linux/). The Python packages for the Flatpak
(`python3-requirements.json`) are taken from `uv.lock`; after changing dependencies, run
`uv run packaging/linux/requirements.py` (CI checks that the file is up to date).

#### Build setup

The build needs Flathub as a **user** remote. `build-linux.sh` installs everything per user
(`--user`), so no root is needed. A system-wide Flathub remote is not used for this.

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
# Only if flatpak-builder is not installed from the distribution:
flatpak install --user flathub org.flatpak.Builder
./build-linux.sh
```

On the first run, flatpak-builder (`--install-deps-from=flathub`) installs from Flathub what the
manifest names: `org.kde.Sdk//6.11`, `org.kde.Platform//6.11` and `io.qt.PySide.BaseApp//6.11`.
It also installs their dependencies: the Locale extensions, `org.kde.KStyle.Adwaita` and the
GL, VAAPI and codec extensions of the freedesktop runtime. `org.flatpak.Builder` also brings
`org.freedesktop.Sdk`. Together this takes roughly 10 GB, mostly the two SDKs; later builds
reuse it. Build state is kept in `.flatpak-builder/` and `build/`.

To test the bundle locally:

```sh
flatpak install --user --reinstall dist/CallSwitcher-*.flatpak
```

Installing it registers Call Switcher for `tel:`, `callto:` and `sip:`. If `mimeapps.list` has no
explicit default for these, the desktop may now open such links with Call Switcher. Set
another app back with, for example, `xdg-mime default linphone.desktop x-scheme-handler/tel`.

To remove the build setup again:

```sh
flatpak uninstall --user org.phonixpbx.callswitcher org.flatpak.Builder io.qt.PySide.BaseApp org.kde.Sdk
flatpak uninstall --user --unused   # runtimes and extensions nothing else needs
flatpak remote-delete --user flathub   # only if no other user Flatpaks come from it
rm -rf .flatpak-builder build
```

### Windows

Requires Python (3.12 or newer, from python.org), [uv](https://docs.astral.sh/uv/) and
[Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`).

```powershell
uv sync --python <path to python.exe>
uv run python -m call_switcher
.\build-windows.ps1 -Python <path to python.exe>
```

The script builds `dist\Call Switcher\` with PyInstaller and the installer
`dist\CallSwitcher-<version>-x64-setup.exe` with Inno Setup
([packaging/windows/CallSwitcher.iss](packaging/windows/CallSwitcher.iss)). The installer
registers the `CallSwitcher.URL` ProgID and the capabilities for `tel:`, `callto:` and `sip:`
in `HKCU`. Regenerate the Windows icon with `uv run packaging/windows/make_ico.py`.

### Code structure

The macOS app and the Linux/Windows app share the dialing and the settings logic
(`dialer.py`, `calls.py`, `settings.py`, `i18n.py`). `macos.py` and the modules at the top
level are macOS only. [call_switcher/qt/](call_switcher/qt/) is the Qt app for Linux and
Windows; only `host_linux.py` and `host_windows.py` differ between the two (phone apps,
default handler, autostart).

### Tests

```sh
uv sync
uv run pytest
```

Tests of the other platform's user interface are skipped.

Regenerate the icon with `uv run assets/make_icon.py`.

All configuration lives in `pyproject.toml`: version, dependencies (`uv.lock` pins them),
pytest and the py2app options including the app's `Info.plist` (`[tool.py2app]`). `setup.py`
only hands those options to py2app, which has no `pyproject.toml` support of its own.

To run without building the bundle or the Flatpak: `uv run python -m call_switcher`. In
this mode `tel:` links do not reach the app, and "Start at login" and "Set as Default" are
disabled. Dialing from the menu still works.

Translations live in [call_switcher/i18n.py](call_switcher/i18n.py). English is the source
language; the tests fail if a translation is missing or its placeholders do not match.

## CI and releases

- `.github/workflows/ci.yml` tests and builds on every push to `main` and on pull requests,
  on macOS 26 and macOS 27 (runner `xcode-27`, still a preview, so failures there do not
  block), on Linux and on Windows. The DMG, the Flatpak and the Windows installer are attached
  to the workflow run as artifacts.
- `.github/workflows/release.yml` creates a GitHub release with the DMG, the Flatpak and the
  Windows installer:

  ```sh
  # Bump the version in pyproject.toml and commit, then:
  git tag v1.1.0 && git push origin v1.1.0
  ```

  The tag must match the version in `pyproject.toml`, otherwise the release fails. For a
  release candidate, set `version = "0.1.0rc1"` and tag `v0.1.0-rc1`; it is published as a
  pre-release.

## License

Apache License 2.0, see [LICENSE](LICENSE) and [NOTICE](NOTICE).
