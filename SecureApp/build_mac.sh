#!/usr/bin/env bash
# Builds dist/<App>.app and dist/<App>-<version>.dmg on macOS.
#
#   bash build_mac.sh                       # uses "python3"
#   PYTHON=python3.13 bash build_mac.sh     # or a specific interpreter
#
set -euo pipefail
cd "$(dirname "$0")"

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "Run this on macOS: a Mac app can only be built on a Mac."
xcode-select -p >/dev/null 2>&1 || fail "Xcode Command Line Tools are missing (PyInstaller needs install_name_tool and lipo).
Install them with:  xcode-select --install"
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || fail "'$PYTHON' not found. Install Python 3.13 from python.org."

step "1/6  Checking Python"
"$PYTHON" - <<'PY' || fail "Unsuitable Python (see the message above)."
import sys, sysconfig
print(f"Python {sys.version.split()[0]} ({sys.executable})")
if not (3, 10) <= sys.version_info[:2] <= (3, 15):
    sys.exit("Python 3.10-3.15 is required (3.13 recommended).")
if not (sysconfig.get_config_var("Py_ENABLE_SHARED") or sysconfig.get_config_var("PYTHONFRAMEWORK")):
    sys.exit("This Python was built without a shared library, which PyInstaller needs.\n"
             "Use the python.org installer, or rebuild it with pyenv:\n"
             '  env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.13')
PY

step "2/6  Virtual environment and dependencies"
[[ -d .venv ]] || "$PYTHON" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements-dev.txt

step "3/6  Automated tests"
python -m pytest

step "4/6  Building the .app with PyInstaller"
APP_NAME="$(python -c 'from secureapp.config import APP_NAME; print(APP_NAME)')"
APP_VERSION="$(python -c 'from secureapp.config import APP_VERSION; print(APP_VERSION)')"
APP_PATH="dist/${APP_NAME}.app"
rm -rf build "dist/${APP_NAME}" "$APP_PATH"
python -m PyInstaller --noconfirm --clean app.spec
[[ -d "$APP_PATH" ]] || fail "PyInstaller did not create $APP_PATH"

step "5/6  Checking the app (signature + self-test)"
if codesign --verify --deep --strict "$APP_PATH"; then
    echo "Code signature: valid (ad-hoc)"
else
    echo "WARNING: code signature check failed"
fi
"$APP_PATH/Contents/MacOS/$APP_NAME" --selftest || fail "The packaged app failed its self-test."

step "6/6  Creating the disk image (.dmg)"
DMG_PATH="dist/${APP_NAME}-${APP_VERSION}.dmg"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
ditto "$APP_PATH" "$STAGING/${APP_NAME}.app"   # ditto preserves symlinks and signatures
ln -s /Applications "$STAGING/Applications"     # the usual "drag here to install" shortcut
rm -f "$DMG_PATH"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING" -fs HFS+ -format UDZO -ov "$DMG_PATH"
hdiutil verify "$DMG_PATH" >/dev/null || fail "The disk image did not pass 'hdiutil verify'."
echo "Disk image checksum: OK"

printf '\n\033[32mDone:\033[0m %s\n' "$DMG_PATH"
printf 'Open it with:  open "%s"\n' "$DMG_PATH"
