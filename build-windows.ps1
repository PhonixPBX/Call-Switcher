# Builds "dist\Call Switcher\" with PyInstaller and the installer
# "dist\CallSwitcher-<version>-x64-setup.exe" with Inno Setup (iscc on the PATH or in its
# default location). Uses the Python from .python-version; -Python overrides it with a
# version or an interpreter path.
param([string]$Python = "")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$syncArgs = @("--locked")
if ($Python) { $syncArgs += @("--python", $Python) }
uv sync @syncArgs
if ($LASTEXITCODE) { exit $LASTEXITCODE }

$py = ".venv\Scripts\python.exe"
$version = & $py -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])'
# Windows wants plain numbers in the file version, so a release candidate like 0.1.0rc1 is 0.1.0.
$numeric = & $py -c "from packaging.version import Version; print(Version('$version').base_version)"

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build\pyinstaller, "dist\Call Switcher"
# Paths are absolute: PyInstaller resolves relative ones against --specpath.
& $py -m PyInstaller --noconfirm --clean --windowed `
    --name "Call Switcher" `
    --icon "$PSScriptRoot\packaging\windows\CallSwitcher.ico" `
    --add-data "$PSScriptRoot\assets\icon.png;assets" `
    --paths "$PSScriptRoot" `
    --exclude-module tkinter `
    --distpath dist --workpath build\pyinstaller --specpath build\pyinstaller `
    packaging\windows\call-switcher.py
if ($LASTEXITCODE) { exit $LASTEXITCODE }

$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $iscc) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
& $iscc /Qp "/DAppVersion=$version" "/DNumericVersion=$numeric" packaging\windows\CallSwitcher.iss
if ($LASTEXITCODE) { exit $LASTEXITCODE }

Write-Host "Done: dist\Call Switcher\ and dist\CallSwitcher-$version-x64-setup.exe"
