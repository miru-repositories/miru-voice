#!/usr/bin/env bash
# Miru Voice — macOS installer
# Installs dependencies, creates a .app bundle, and optionally adds it to the Dock.
#
# Usage:
#   cd macos/
#   bash scripts/install.sh          # install + create .app
#   bash scripts/install.sh --dock   # also pin to the Dock

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MACOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_NAME="Miru Voice"
APP_BUNDLE="$HOME/Applications/MiruVoice.app"

# ── Helpers ──────────────────────────────────────────────────────────────────

info()  { printf '\033[1;34m==> %s\033[0m\n' "$*"; }
ok()    { printf '\033[1;32m  ✓ %s\033[0m\n' "$*"; }
warn()  { printf '\033[1;33m  ! %s\033[0m\n' "$*"; }
fail()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ── Pre-flight checks ───────────────────────────────────────────────────────

info "Checking prerequisites"

# Find a suitable Python (3.11 or 3.12 preferred — 3.13+ lacks PyTorch wheels on x86)
PYTHON=""
for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        py_ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major="${py_ver%%.*}"
        minor="${py_ver##*.}"
        if [[ "$major" -eq 3 ]] && [[ "$minor" -ge 11 ]] && [[ "$minor" -le 12 ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    fail "Python 3.11 or 3.12 is required (3.13+ not yet supported due to PyTorch).
  Install with:  brew install python@3.12"
fi
ok "Python: $($PYTHON --version)"

# Check for pkg-config and ffmpeg (needed to build PyAV)
for tool in pkg-config ffmpeg; do
    if ! command -v "$tool" &>/dev/null; then
        if command -v brew &>/dev/null; then
            info "Installing $tool via Homebrew"
            brew install "$tool"
        else
            fail "$tool is required. Install Homebrew first (https://brew.sh) then: brew install $tool"
        fi
    fi
done
ok "pkg-config and ffmpeg available"

# ── Virtual environment ──────────────────────────────────────────────────────

VENV_DIR="$MACOS_DIR/.venv"

if [[ -d "$VENV_DIR" ]]; then
    info "Existing venv found at $VENV_DIR — reusing"
else
    info "Creating virtual environment"
    "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
ok "venv activated ($VENV_DIR)"

# ── Install dependencies ─────────────────────────────────────────────────────

info "Installing dependencies (this may take a few minutes)"
pip install --upgrade pip --quiet
pip install -e "$MACOS_DIR[dev]" --quiet
# torch 2.2 was built against NumPy 1.x; numpy 2.x causes runtime crashes
pip install "numpy<2" --quiet
ok "All Python dependencies installed"

# ── Generate app icon ────────────────────────────────────────────────────────

info "Generating app icon"

ICON_TMP="$(mktemp -d)/miru_icon"
mkdir -p "$ICON_TMP.iconset"

python3 -c "
from PIL import Image, ImageDraw

size = 512
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Background circle
draw.ellipse([20, 20, size-20, size-20], fill=(88, 28, 135))
draw.ellipse([40, 40, size-40, size-40], fill=(124, 58, 237))

# Microphone body
cx, cy = size//2, size//2 - 30
draw.rounded_rectangle([cx-40, cy-80, cx+40, cy+80], radius=40, fill=(255, 255, 255))

# Mic arc
for i in range(3):
    o = 8 + i*2
    draw.arc([cx-70-o, cy-20-o, cx+70+o, cy+120+o], start=0, end=180, fill=(255, 255, 255, 200), width=6)

# Stand
draw.line([cx, cy+120, cx, cy+160], fill=(255, 255, 255), width=8)
draw.line([cx-40, cy+160, cx+40, cy+160], fill=(255, 255, 255), width=8)

# Sound waves
for i in range(3):
    r = 120 + i*30
    draw.arc([cx-r, cy-r+40, cx+r, cy+r+40], start=210, end=270, fill=(255, 255, 255, 150-i*40), width=4)
    draw.arc([cx-r, cy-r+40, cx+r, cy+r+40], start=270, end=330, fill=(255, 255, 255, 150-i*40), width=4)

img.save('$ICON_TMP.png')
"

for s in 16 32 64 128 256 512; do
    sips -z "$s" "$s" "$ICON_TMP.png" --out "$ICON_TMP.iconset/icon_${s}x${s}.png" >/dev/null 2>&1
done
for s in 16 32 128 256; do
    s2=$((s * 2))
    cp "$ICON_TMP.iconset/icon_${s2}x${s2}.png" "$ICON_TMP.iconset/icon_${s}x${s}@2x.png" 2>/dev/null || true
done

ok "Icon generated"

# ── Create .app bundle ───────────────────────────────────────────────────────

info "Creating $APP_BUNDLE"

mkdir -p "$HOME/Applications"
rm -rf "$APP_BUNDLE"

# Use osacompile to create a properly signed .app that macOS trusts.
# The AppleScript launches miru-voice in the background with the correct PATH.
osacompile -o "$APP_BUNDLE" -e "
do shell script \"export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:\$PATH; source $VENV_DIR/bin/activate; $VENV_DIR/bin/miru-voice >> ~/Library/Logs/miru-voice.log 2>&1 &\"
"

# Replace the default AppleScript icon with our custom one
ICNS_FILE="$APP_BUNDLE/Contents/Resources/applet.icns"
iconutil -c icns "$ICON_TMP.iconset" -o "$ICNS_FILE" 2>/dev/null || \
    warn "Could not generate .icns — app will use a generic icon"
touch "$APP_BUNDLE"

ok "$APP_BUNDLE created"

# ── Dock (optional) ──────────────────────────────────────────────────────────

if [[ "${1:-}" == "--dock" ]]; then
    info "Adding Miru Voice to the Dock"
    defaults write com.apple.dock persistent-apps -array-add \
        "<dict><key>tile-data</key><dict><key>file-data</key><dict>\
<key>_CFURLString</key><string>$APP_BUNDLE</string>\
<key>_CFURLStringType</key><integer>0</integer>\
</dict></dict></dict>"
    killall Dock
    ok "Added to Dock (Dock restarted)"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
info "Installation complete!"
echo ""
echo "  To run from Terminal:"
echo "    cd $MACOS_DIR && source .venv/bin/activate && miru-voice"
echo ""
echo "  To run from Dock/Finder:"
echo "    open \"$APP_BUNDLE\""
echo ""
echo "  To add to Dock later:"
echo "    bash $SCRIPT_DIR/install.sh --dock"
echo ""
warn "First run: grant Accessibility permission to Python in"
warn "  System Settings > Privacy & Security > Accessibility"
