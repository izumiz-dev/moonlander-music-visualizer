# Oryx Source Directory

This directory is the designated place for your original Moonlander firmware source code downloaded from [Oryx](https://configure.zsa.io/moonlander).

## How to Update Your Layout

1.  Make your keymap changes on Oryx.
2.  Download the "Source" (zip file).
3.  Unzip the contents. You will see a folder name like `zsa_moonlander_...`.
4.  Place that **entire folder** inside this directory (`firmware/oryx_source/`).
    -   Example: `firmware/oryx_source/zsa_moonlander_my_layout_v10/`

## Applying Music Visualizer

Once your new source is here, follow the instructions in the [Root README](../../README.md) to integrate the Music Visualizer features:

1.  Copy `musicviz_core.c` and `musicviz.h` and `rgb_matrix_user.inc` from `portable_musicviz/` into your new folder.
2.  Add `SRC += musicviz_core.c` to your `rules.mk`.
3.  Include `musicviz.h` in your `keymap.c`.
4.  Include `rgb_matrix_user.inc` in your `rgb_matrix_user.inc` (or create it).

(See root README for detailed steps)
