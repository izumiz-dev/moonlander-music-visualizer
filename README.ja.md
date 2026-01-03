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
│   ├── screen_analyzer.py          # 画面キャプチャと色抽出
│   ├── hid_sender.py               # Raw HID 通信
│   └── main.py                     # CLI エントリーポイント
├── firmware/
│   └── oryx_source/                # [入力] Oryx のソース zip の中身をここに配置
├── portable_musicviz/              # [ライブラリ] ビジュアライザーのロジック (C コード)
│   ├── musicviz.h                  # 状態定義
│   ├── rgb_matrix_user.inc         # ビジュアライザーエフェクトの実装
│   └── rules.inc.mk                # ビルドルール
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

### 2. ファームウェア側 (Moonlander)

このプロジェクトは、既存の Oryx レイアウトにビジュアライザーを「注入」するように設計されています。

1.  **ソースのエクスポート:** [Oryx](https://configure.zsa.io) からレイアウトのソースコードをダウンロードします。
2.  **配置:** フォルダを `firmware/oryx_source/` に解凍します。
3.  **ビルド:** ビルドスクリプトを実行します。自動的にソースを見つけ、ビジュアライザーのコードを注入してコンパイルします。
    ```bash
    ./build_firmware.sh
    ```
4.  **書き込み:** [Keymapp](https://blog.zsa.io/keymapp/) または `qmk flash` を使用して、`~/qmk_firmware/` に生成された `.bin` ファイルを書き込みます。

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