# Moonlander Music Visualizer for Windows

このプロジェクトを Windows 環境で実行するためのセットアップガイドです。
WSL (Linux) を経由せず、Windows ネイティブで動作させることを推奨します（キーボード入力を維持したまま LED 制御が可能です）。

## 前提条件

1.  **Moonlander キーボード**
    *   **書き込み済みであること:** すでに Music Visualizer 対応のファームウェアが書き込まれている必要があります。（注: Windows 上でのファームウェアビルドはこのスクリプトでは現在サポートされていません）
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

3.  **録音デバイスの設定**
    *   「サウンドの設定」 > 「録音」タブを開きます。
    *   **「CABLE Output (VB-Audio Virtual Cable)」** を右クリックし、**「既定のデバイス」** に設定します。

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
