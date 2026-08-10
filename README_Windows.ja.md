# Moonlander Music Visualizer for Windows

このプロジェクトを Windows 環境で実行するためのセットアップガイドです。
WSL (Linux) を経由せず、Windows ネイティブで動作させることを推奨します（キーボード入力を維持したまま LED 制御が可能です）。

## 前提条件

1.  **Moonlander キーボード**
    *   Music Visualizer 対応のファームウェアが必要です。未書き込みの場合は [4. ファームウェアのビルド](#4-ファームウェアのビルド) を参照してください。QMK MSYS を使って Windows ネイティブでビルドできます。
2.  **Windows 10 / 11**
3.  **Python 3.11 以降**
    *   Microsoft Store または公式サイトからインストールしてください。
4.  **VB-CABLE (仮想オーディオデバイス)**
    *   PCの再生音（YouTubeなど）を取り込むために必要です。
    *   [VB-AUDIO Software](https://vb-audio.com/Cable/) から無料でダウンロード・インストールできます。

---

## 1. オーディオ設定 (重要)

Windows の音を Visualizer に送るための設定です。

1.  **VB-CABLE のインストール**
    *   ダウンロードした ZIP を解凍し、`VBCABLE_Setup_x64.exe` を右クリックして「管理者として実行」でインストールします。
    *   インストール後、PC を**再起動**してください。

2.  **再生デバイスの設定**
    *   タスクバーのスピーカーアイコンをクリックし、再生デバイスを **「CABLE Input (VB-Audio Virtual Cable)」** に切り替えます。
    *   ※これでPCの音が仮想ケーブルに流れます。

3.  **録音デバイスの設定** *(任意)*
    *   「サウンドの設定」 > 「録音」タブを開きます。
    *   **「CABLE Output (VB-Audio Virtual Cable)」** を右クリックし、**「既定のデバイス」** に設定します。
    *   *必須ではありません:* `main.py` の `find_audio_device()` はデバイスを**名前で検索**するため、既定の録音デバイスが別のものでも CABLE Output を自動的に拾います。実際に効くのは上の手順2の方です。

> **補足: スピーカーから音を聞く方法**
> 再生デバイスを CABLE Input にすると、スピーカーから音が聞こえなくなります。
> これを回避するには、録音タブの **「CABLE Output」** をダブルクリック > **「聴く」** タブ > **「このデバイスを聴く」** にチェックを入れ、再生するデバイスに「普段使っているスピーカー/ヘッドホン」を選択してください。

---

## 2. プロジェクトのセットアップ

PowerShell を使用して環境を構築します。

### ツール管理ツール `mise` を使う場合 (推奨)
1.  **mise のインストール** (未導入の場合):
    ```powershell
    irm https://mise.jdx.dev/install.ps1 | iex
    # 一度 PowerShell を再起動
    ```
2.  **依存ライブラリのインストール**:
    プロジェクトフォルダで以下を実行します。
    ```powershell
    mise run install
    ```
    ※ エラーが出る場合は、PowerShell の実行ポリシーを許可してください:
    `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 手動で Python を使う場合
1.  **ライブラリのインストール**:
    ```powershell
    python -m pip install -r requirements.txt
    ```

---

## 3. 実行方法

### 通常モード
PCの音に合わせてキーボードが光ります。

```powershell
# mise を使う場合
mise run live

# 手動の場合
python -m moonlander_musicviz.main
```

---

## 4. ファームウェアのビルド

キーボードにまだ Music Visualizer が入っていない場合や、Oryx でレイアウトを変更した場合に必要です。
ビルドは **QMK MSYS** 上で行います。QMK MSYS は bash を同梱しているため、macOS で使うのと同じ
`build_firmware.sh` がそのまま動きます。

### 4.1 QMK MSYS のインストール

[msys.qmk.fm](https://msys.qmk.fm/) からインストーラを入手して実行し、**QMK MSYS** ターミナルを開いて:

```bash
qmk setup
```

`qmk_firmware`（サブモジュール込みで約 2GB）が `C:\Users\<ユーザー名>\qmk_firmware` にクローンされます。
これは `build_firmware.sh` が期待するパスと一致しています。最後に `qmk doctor` を実行し、
`arm-none-eabi-gcc` のバージョンが表示されることを確認してください。

> **`qmk doctor` で `Failed to compile a simple program with arm-none-eabi-gcc, return code 127` と出る場合:**
> ツールチェーンは `/opt/qmk` にありますが、動作に必要な `libwinpthread-1.dll`（`/mingw64/bin` にある）が
> PATH に入っていないのが原因です。以下の内容で
> `C:\QMK_MSYS\etc\profile.d\zzz-qmk-mingw-dll-path.sh` を作成すると恒久的に解決します:
> ```sh
> export PATH="$PATH:/mingw64/bin"
> ```
> 先頭ではなく**末尾**に追加してください。mingw 側のツールが QMK のものを覆い隠さないようにするためです。

> **`qmk` コマンド自体が見つからない場合**、インストーラの CLI 導入工程が失敗しています。手動で入れてください:
> ```bash
> UV_TOOL_DIR=/opt/uv/tools UV_TOOL_BIN_DIR=/opt/uv/tools/bin /opt/uv/uv.exe tool install qmk
> ```

### 4.2 Oryx ソースの取得

[Oryx](https://configure.zsa.io/moonlander) で自分のレイアウトを開き、コンパイル済みの `.bin` ではなく
**Source**（zip）をダウンロードします。**`.bin` はベースにできません** — ビジュアライザはソースレベルで
マージされるためです。

解凍して、`rules.mk` を含む内側のフォルダを `firmware/oryx_source/` に配置します:

```
firmware/oryx_source/zsa_moonlander_<レイアウト名>_source/
```

### 4.3 ビルドと書き込み

PowerShell ではなく **QMK MSYS** のターミナルから実行します:

```bash
cd /c/Users/<ユーザー名>/Repositories/moonlander-music-visualizer
./build_firmware.sh
```

`C:\Users\<ユーザー名>\qmk_firmware\zsa_moonlander_my_musicviz_automerge.bin` が生成されます。
[Keymapp](https://blog.zsa.io/keymapp/) を開き、**Select Firmware** からこのファイルを指定してください。

書き込み後は、RGB モードを `musicviz` まで送ってください。カスタムエフェクトはリストの**末尾**に
追加されるため、Moonlander の約45種類の内蔵アニメーションを通過する必要があります（モードキーの
長押しが楽です）。選択内容は EEPROM に保存されるので、この操作は最初の一度だけです。

> **改行コードに注意。** `.gitattributes` で `*.sh` と `*.mk` を LF に固定しています。これを迂回すると
> Windows の CRLF により bash が `$'\r': command not found` で停止し、make 変数にも CR が紛れ込みます。

---

## トラブルシューティング

### Q. 光らない
*   **キーボードのモード確認:**
    Moonlander の「LEDモード切り替えキー」を何度か連打して、Visualizer モード（通常はリストの末尾）に合わせてください。
*   **輝度確認:**
    キーボードの LED 輝度設定が 0 になっていませんか？輝度アップキーを押してください。
*   **通信確認:**
    実行ログに `[HID] Opened: ZSA Technology Labs ...` と表示されているか確認してください。

### Q. 音に反応しない（ダッシュボードが動かない）
*   **入力デバイスの確認:**
    実行時に `[+] Using device: CABLE Output ...` と表示されていますか？
*   **Windowsの設定確認:**
    「CABLE Output」が「既定の録音デバイス」になっているか、インジケーター（音量バー）が動いているか確認してください。

### Q. エラーが出る (`ModuleNotFoundError`)
*   ライブラリが不足しています。以下を実行して再インストールしてください。
    ```powershell
    python -m pip install -r requirements.txt
    ```
*   特に `rich` モジュールが見つからないエラーがよくあります。その場合は `python -m pip install rich` を個別に実行してください。

### Q. WSL では動かないの？
*   WSL でも動かせますが、**キーボード入力が Windows 側で使えなくなる**（USBパススルーの仕様）ため推奨しません。この Windows ネイティブ手順であれば、キーボード入力を維持したまま光らせることができます。
