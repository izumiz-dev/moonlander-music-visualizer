# Moonlander Music Visualizer

[English](README.md)

このプロジェクトは、**ZSA Moonlander** キーボードを高性能かつ低レイテンシの音楽および画面ビジュアライザーに変身させます。PC の音声（低音、中音、高音）と画面のコンテンツをリアルタイムで解析し、美しいカスタム RGB エフェクトを駆動します。

## デモ

[![Moonlander Music Visualizer Demo](https://img.youtube.com/vi/_oECPrUgOGk/0.jpg)](https://www.youtube.com/watch?v=_oECPrUgOGk)

## 特徴

-   **画面カラー同期 (Screen Color Sync - New!):** メインディスプレイの主要な色をリアルタイムでキャプチャし、映画や MV の雰囲気に合わせてキーボードのバックライトを同期させます。
-   **対称ラジアルウェーブ (Symmetric Radial Waves):** キーボード（USB 接続側）の中心から外側に向かって色が対称に広がり、左右のユニットが離れていても一体感のあるシームレスな外観を作り出します。
-   **3バンドオーディオ解析:** 音声を低音 (Bass)、中音 (Mid)、高音 (Treble) のエンベロープに正確に分離し、明るさや波の広がりを変調させます。
-   **アダプティブブライトネス:** 音量の大きさに応じて全体のマスター輝度を変調し、ダイナミックなコントラストを実現します。
-   **高性能:** 最適化された Python バックエンド (NumPy, MSS) と効率的な QMK C ファームウェアレンダリングを使用しています。

## ディレクトリ構造

```
.
├── moonlander_musicviz/            # [ホスト] Python アプリ
│   ├── audio_analyzer.py           # FFT ロジック
│   ├── screen_analyzer.py          # 画面キャプチャの統括と色抽出
│   ├── screen_backends.py          # 画面キャプチャのバックエンド (mss, Windows では dxcam)
│   ├── color_utils.py              # 円環 hue の演算 (0-255 の輪の上での平均化・平滑化)
│   ├── hid_sender.py               # Raw HID 通信
│   └── main.py                     # CLI エントリーポイント
├── firmware/
│   └── oryx_source/                # [入力] Oryx のソース zip の中身をここに配置
├── portable_musicviz/              # [ライブラリ] ビジュアライザーのロジック (C コード)
│   ├── musicviz.h                  # 状態定義
│   ├── rgb_matrix_user.inc         # ビジュアライザーエフェクトの実装
│   ├── rules.inc.mk                # ビルドルール (keymap の rules.mk に追記される)
│   └── config.inc.h                # キーコード互換定義 (keymap の config.h に追記される)
└── build_firmware.sh               # 自動ビルドスクリプト (Oryx ソース + Musicviz をマージ)
```

## 🚀 インストールと使い方

### 1. ホスト側 (Python)

**要件:**
-   Python 3.11+
-   [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole) (macOS でのオーディオループバック用)

**セットアップ:**
```bash
# Python の依存関係をインストール
pip install -r requirements.txt
```

**実行:**

*   **ミュージックモード (デフォルト):**
    音声を解析し、プリセットのカラーパレットを使用します。
    ```bash
    python -m moonlander_musicviz.main
    ```

*   **画面同期モード:**
    リズム解析のために音声を使用し、*さらに* パレット用に画面の色をキャプチャします。
    ```bash
    python -m moonlander_musicviz.main --screen
    ```
    `--screen-monitor`（既定値 `primary`）でキャプチャするディスプレイを、`--screen-fps` で
    キャプチャ頻度を指定できます。Windows では Desktop Duplication API を使ってキャプチャします。
    詳細と DRM 保護動画に関する（回避不能な、OSレベルの）制約については
    [README_Windows.ja.md](README_Windows.ja.md#画面色シンク) を参照してください。

### 2. ファームウェア側 (Moonlander)

このプロジェクトは、既存の Oryx レイアウトにビジュアライザーを「注入」するように設計されています。

`qmk setup` 済みの環境（`~/qmk_firmware` と `qmk` CLI）が必要です。Windows の場合は QMK MSYS を使います。
[README_Windows.ja.md](README_Windows.ja.md#4-ファームウェアのビルド) を参照してください。

1.  **ソースのエクスポート:** [Oryx](https://configure.zsa.io) からレイアウトの **Source**（zip）をダウンロードします。
    コンパイル済みの `.bin` はベースにできません。ビジュアライザはソースレベルでマージされるためです。
2.  **配置:** フォルダを `firmware/oryx_source/` に解凍します。
3.  **ビルド:** ビルドスクリプトを実行します。自動的にソースを見つけ、ビジュアライザーのコードを注入してコンパイルします。
    ```bash
    ./build_firmware.sh
    ```
4.  **書き込み:** [Keymapp](https://blog.zsa.io/keymapp/) の **Select Firmware**、または `qmk flash` を使用して、`~/qmk_firmware/` に生成された `.bin` ファイルを書き込みます。
5.  **エフェクトの選択:** RGB モードを `musicviz` まで送ります。カスタムエフェクトはリストの**末尾**に追加されるため、
    約45種類の内蔵アニメーションを通過することになります。選択内容は EEPROM に保存されます。

### Oryx のエクスポートを upstream QMK でビルドする

Oryx は ZSA のフォーク向けにコードを生成するため、エクスポートしたままでは upstream QMK でコンパイルできません。
`build_firmware.sh` が以下を自動的に調整します（手動ビルドする場合に把握しておくとよい内容です）:

-   `ORYX_ENABLE = no` — ビジュアライザが Raw HID を占有するため、Oryx のハンドラと競合させられません。
    `keymap.c` 内の `rawhid_state.rgb_control` は `0` に書き換えられ、リンカを満足させるために
    `musicviz_core.c` がダミーの `webhid_leds` を定義します。
-   `RGB_MATRIX_CUSTOM_KB = no` — Oryx はこれを `yes` にしますが、それにより
    `keyboards/zsa/moonlander/rgb_matrix_kb.inc` が要求されます。このファイルは ZSA のフォークにしか存在しません。
-   `keymap.json` を削除 — 新しいエクスポートは `"modules": ["zsa/oryx", "zsa/defaults"]` を宣言しますが、
    upstream に `modules/zsa` は存在しません。
-   `config.inc.h` が、Oryx の出力する旧 `RGB_*` キーコード名を現行の `RM_*` にマッピングします
    (`RGB_TOG` → `RM_TOGG`、`RGB_MODE_FORWARD` → `RM_NEXT` など)。

**トレードオフ:** `ORYX_ENABLE = no` が必須のため、Keymapp のライブ機能（ライブトレーニング、ヒートマップ）と
Oryx のライブ RGB プレビューは使えなくなります。キー配置・レイヤー・マクロ・レイヤーごとの色設定は影響を受けず、
Keymapp からの書き込みも従来どおり可能です。

## ⚙️ 技術的な詳細

-   **対称ロジック:** ファームウェアは両方のキーボードハーフの「内側の端」を自動的に計算し、ユニットをどれだけ離して配置しても、光の波が中心から完全に対称に広がるようにします。
-   **鮮やかな色 (Vivid Colors):** 画面同期モードでは、アナライザーがキャプチャした色の彩度を強調し、暗いシーンや淡いシーンでもキーボードが常に鮮やかで際立った色で光るようにします。

## ⚠️ 注意点

-   **パフォーマンス:** 画面キャプチャは最適化（ダウンサンプリング）されており、最小限の CPU 使用率で約 30fps を維持します。

<details>
<summary><b>🎧 オーディオ設定の詳細 (macOS の安定性)</b></summary>

BlackHole を複数出力装置 (Multi-Output Device) で使用する際の音飛びやノイズを防ぐため、**Audio MIDI 設定** で以下の手順に従ってください:

1.  **複数出力装置の作成:** `+` アイコンをクリックし、`複数出力装置を作成` を選択します。
2.  **マスター装置:** **マスター装置**（またはクロックソース）を **物理ハードウェア**（例: *外部ヘッドフォン*、*MacBook Proのスピーカー*、*DAC* など）に設定します。BlackHole をマスターに設定しないでください。
3.  **ドリフト補正:** **BlackHole 2ch** のみ **ドリフト補正** を有効にします。マスターの物理デバイスでは無効のままにしてください。
4.  **サンプルレート:** 複数出力装置内のすべてのサブデバイスが同じサンプルレート（例: **48,000 Hz**）に設定されていることを確認します。
5.  **デバイスの順序:** サブデバイスのリストで、物理デバイスが *最初* にチェックされている（リストの一番上に表示されている）ことを確認します。

この構成により、仮想ドライバ (BlackHole) がハードウェアのクロックと完全に同期し、ラグやグリッチのない体験が保証されます。
</details>