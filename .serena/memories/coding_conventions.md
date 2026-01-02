# Coding Conventions

## Python
- **Style**: PEP 8に準拠。
- **Docstrings**: クラスやメソッドには、その目的と入出力を説明するdocstringを記述する（仕様書の例では三重引用符 `"""` を使用）。
- **Typing**: 型ヒントの明示的な使用は必須ではないが、可読性のために検討する。
- **Naming**: クラス名は `PascalCase`（例: `AudioAnalyzer`）、関数・変数・ファイル名は `snake_case`。
- **Packages**: メインのロジックは `moonlander_musicviz` パッケージ内に配置する。

## Firmware (C/QMK)
- `keymap.c` や `rgb_matrix_user.inc` の既存のQMKスタイルに従う。
- コメントを用いて各セクション（ユーティリティ、エフェクト等）を明確に分ける。
