#!/bin/bash
set -e

# Configuration
QMK_HOME="$HOME/qmk_firmware"
KEYBOARD="zsa/moonlander"
# The name of the keymap directory in QMK
TARGET_KEYMAP_NAME="my_musicviz_automerge"

# Paths
ORYX_SRC_ROOT="./firmware/oryx_source"
LIB_DIR="./portable_musicviz"
DEST_DIR="$QMK_HOME/keyboards/$KEYBOARD/keymaps/$TARGET_KEYMAP_NAME"

# 1. Check for Oryx Source
# We look for any directory inside firmware/oryx_source
FOUND_DIR=$(find "$ORYX_SRC_ROOT" -mindepth 1 -maxdepth 1 -type d | head -n 1)

if [ -z "$FOUND_DIR" ]; then
    echo "[!] No Oryx source found in $ORYX_SRC_ROOT."
    echo "[*] Falling back to integrated reference: ./firmware/moonlander_musicviz_integrated"
    SRC_DIR="./firmware/moonlander_musicviz_integrated"
else
    echo "[*] Found Oryx source container: $FOUND_DIR"
    
    # Oryx zips often have a nested structure (Wrapper Dir -> Source Dir -> keymap.c).
    # We need to find the ACTUAL source directory containing 'rules.mk' or 'keymap.c'.
    REAL_BS_DIR=$(find "$FOUND_DIR" -name "rules.mk" -exec dirname {} \; | head -n 1)
    
    if [ -z "$REAL_BS_DIR" ]; then
        echo "[!] Error: Found a folder but it doesn't contain 'rules.mk'. Is it a valid QMK source?"
        exit 1
    fi
    
    SRC_DIR="$REAL_BS_DIR"
    echo "[*] Detected real source root at: $SRC_DIR"
fi

echo "[*] Preparing build directory: $DEST_DIR"
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

# 2. Copy Base Keymap (Oryx or Integrated)
echo "[*] Copying base keymap from $SRC_DIR..."
# Copy contents recursively, preserving attributes
cp -R "$SRC_DIR/"* "$DEST_DIR/"

# Remove keymap.json if it exists, as it takes precedence over keymap.c
# and we need to compile the C file where we add our headers.
if [ -f "$DEST_DIR/keymap.json" ]; then
    echo "[*] Removing keymap.json to favor keymap.c compilation..."
    rm "$DEST_DIR/keymap.json"
fi

# 3. Merge Music Visualizer Library
echo "[*] Merging Music Visualizer Library from $LIB_DIR..."
cp "$LIB_DIR/musicviz.h" "$DEST_DIR/"
cp "$LIB_DIR/musicviz_core.c" "$DEST_DIR/"
cp "$LIB_DIR/rgb_matrix_user.inc" "$DEST_DIR/"

# Patch keymap.c to handle ORYX_ENABLE=no (suppress rawhid_state usage)
# We replace 'rawhid_state.rgb_control' with '0' so the checks always fail (Oryx not controlling).
# Note: macOS sed requires empty string for backup extension.
if [ -f "$DEST_DIR/keymap.c" ]; then
    echo "[*] Patching keymap.c to remove Oryx dependencies..."
    sed -i '' 's/rawhid_state.rgb_control/0/g' "$DEST_DIR/keymap.c"
fi

# 4. Inject Rules (if not already present)
RULES_MK="$DEST_DIR/rules.mk"
if ! grep -q "musicviz_core.c" "$RULES_MK"; then
    echo "[*] Injecting build rules into rules.mk..."
    # Ensure there's a newline before appending
    echo "" >> "$RULES_MK"
    cat "$LIB_DIR/rules.inc.mk" >> "$RULES_MK"
else
    echo "[*] rules.mk already seems patched, skipping injection."
fi

# 5. Compile
echo "[*] Compiling firmware ($TARGET_KEYMAP_NAME)..."
cd "$QMK_HOME"
qmk compile -kb "$KEYBOARD" -km "$TARGET_KEYMAP_NAME"

echo "---------------------------------------------------"
echo "[+] Build complete!"
echo "[+] Firmware file: $QMK_HOME/${KEYBOARD//\//_}_${TARGET_KEYMAP_NAME}.bin"
echo "---------------------------------------------------"
