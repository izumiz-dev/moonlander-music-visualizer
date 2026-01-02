# Suggested Commands

## Environment & Dependency Management
- `mise run install`: Pythonの依存関係をインストールし、venvをセットアップする。
- `mise run clean`: venvやキャッシュファイルを削除する。

## Audio Setup & Discovery
- `brew install blackhole-2ch`: BlackHoleオーディオドライバーをインストールする。
- `mise run list-devices`: 利用可能なオーディオ入力デバイスを表示し、BlackHoleを検出する。

## Execution
- `mise run run`: ビジュアライザーを起動する（オーディオキャプチャ → キーボードへの送信）。

## Firmware (QMK)
- `qmk compile -kb zsa/moonlander -km <YOUR_KEYMAP>`: ファームウェアをビルドする。
