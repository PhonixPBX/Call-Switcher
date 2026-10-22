<img src="assets/icon.png" width="128" alt="Call Switcher icon">

# Call Switcher

A macOS menu bar app that handles `tel:`, `callto:` and `sip:` links. It places the call
through a phone app (such as Telephone.app), the click-to-call API of
[PhonixPBX](https://github.com/PhonixPBX/PhonixPBX), or Asterisk ARI (originate).

Runs on macOS 26 and 27 (Apple Silicon). Available in English, German, French, Italian,
Spanish and Portuguese (Brazil). The app follows the language order in System Settings →
General → Language & Region and falls back to English.

## Installation

1. Open the DMG and drag "Call Switcher" onto the "Applications" folder.
2. Open the app. macOS blocks it the first time because it is not notarized. Go to
   System Settings → Privacy & Security and click **Open Anyway** next to "Call Switcher",
   then confirm. Alternatively, in Terminal:
   `xattr -dr com.apple.quarantine "/Applications/Call Switcher.app"`
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

Tests:

```sh
uv sync
uv run pytest
```

Regenerate the icon with `uv run assets/make_icon.py`.

All configuration lives in `pyproject.toml`: version, dependencies (`uv.lock` pins them),
pytest and the py2app options including the app's `Info.plist` (`[tool.py2app]`). `setup.py`
only hands those options to py2app, which has no `pyproject.toml` support of its own.

To run without building the bundle: `uv run python -m call_switcher`. In this mode
`tel:` links do not reach the app, and "Start at login" and "Set as Default" are disabled.
Dialing from the menu still works.

Translations live in [call_switcher/i18n.py](call_switcher/i18n.py). English is the source
language; the tests fail if a translation is missing or its placeholders do not match.

## CI and releases

- `.github/workflows/ci.yml` tests and builds on every push to `main` and on pull requests,
  on macOS 26 and macOS 27 (runner `xcode-27`, still a preview, so failures there do not
  block). The DMG is attached to the workflow run as an artifact.
- `.github/workflows/release.yml` creates a GitHub release with the DMG:

  ```sh
  # Bump the version in pyproject.toml and commit, then:
  git tag v1.1.0 && git push origin v1.1.0
  ```

  The tag must match the version in `pyproject.toml`, otherwise the release fails. For a
  release candidate, set `version = "0.1.0rc1"` and tag `v0.1.0-rc1`; it is published as a
  pre-release.

## License

Apache License 2.0, see [LICENSE](LICENSE) and [NOTICE](NOTICE).
