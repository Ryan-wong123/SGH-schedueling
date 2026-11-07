#!/usr/bin/env bash
# Builds the standalone GLF Assessment Scheduler for macOS.
# PyInstaller cannot cross-compile, so this must be run on a Mac.
# Usage: ./scripts/build-mac.sh [--skip-install]

set -euo pipefail

SKIP_INSTALL=0
if [[ "${1:-}" == "--skip-install" ]]; then
    SKIP_INSTALL=1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
VENV_DIR="$ROOT/venv-mac"
VENV_PYTHON="$VENV_DIR/bin/python"
SPEC_FILE="$ROOT/GLF Scheduler.spec"
APP_FILE="$ROOT/dist/GLF Assessment Scheduler"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This script builds the macOS app and must be run on a Mac." >&2
    echo "(On Windows, use scripts/build-exe.ps1.)" >&2
    exit 1
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3 is required on the build computer to create the app." >&2
        exit 1
    fi
    python3 -m venv "$VENV_DIR"
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "Node.js/npm is required on the build computer to compile the frontend." >&2
    exit 1
fi

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
    (cd "$BACKEND_DIR" && "$VENV_PYTHON" -m pip install -r requirements.txt && "$VENV_PYTHON" -m pip install pyinstaller)
    (cd "$FRONTEND_DIR" && npm install)
fi

(cd "$FRONTEND_DIR" && npm run build)

(cd "$ROOT" && "$VENV_PYTHON" -m PyInstaller --clean --noconfirm "$SPEC_FILE")

echo
echo "Created standalone application:"
echo "$APP_FILE"
echo
echo "Copy this file to another Mac and run it. If macOS blocks it because it was"
echo "downloaded, run:  xattr -d com.apple.quarantine \"GLF Assessment Scheduler\""
echo "then  chmod +x \"GLF Assessment Scheduler\"  and open it from Terminal or double-click it."
echo "Note: the build matches the Mac's CPU (Apple Silicon vs Intel)."
