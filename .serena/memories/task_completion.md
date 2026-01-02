# Task Completion Checklist

タスクを完了した際は、以下の手順で動作を確認すること：

1. **Dependency Check**: 依存関係に変更があった場合は、`mise run install` が正常に動作することを確認する。
2. **Device Discovery**: `mise run list-devices` を実行し、オーディオデバイスが正しく認識されているか確認する。
3. **Runtime Verification**: `mise run run` を実行し、エラーなくオーディオの解析とHID送信が開始されることを確認する。
4. **Log Analysis**: コンソールに出力される解析結果（bass, mid, treble, beat等）が意図した通りか確認する。
5. **Firmware Sync**: ファームウェア側の変更がある場合は、コンパイルが通り、プロトコル定義（32バイトパケット）に齟齬がないか確認する。
