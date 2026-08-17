# 05_permission_prompt_reduction

- 日付: 2026-08-13
- 位置づけ: Claude Codeの権限確認プロンプトを削減するために行った設定変更の記録

## 背景

ファイル編集・コマンド実行のたびに許可確認が挟まることが不快との指摘があり、原因の洗い出しと対策を実施した。

## 実施した変更

`.claude/settings.json`に`permissions.defaultMode: "bypassPermissions"`を追加。

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions",
    "allow": ["Bash(*)", "Write", "Edit"]
  }
}
```

併せて、上位設定（ユーザーグローバル`~/.claude/settings.json`、エンタープライズ管理設定
`C:\Program Files\ClaudeCode\managed-settings.json`、レジストリポリシー`HKLM/HKCU:\SOFTWARE\Policies\ClaudeCode`）に
これを上書きする`deny`ルールが存在しないことを確認済み（いずれも未設定）。

## 追記：VSCode拡張側にも別のスイッチが必要だった

`.claude/settings.json`の`bypassPermissions`だけでは不十分で、VSCode拡張のユーザー設定
（`%APPDATA%\Code\User\settings.json`）に`claudeCode.allowDangerouslySkipPermissions: true`を
追加しないと、拡張機能側が安全側に倒して結局確認を挟むことが判明した。個人設定のため
プロジェクトのgit管理には含まれない。VSCodeの「ウィンドウの再読み込み」後に反映を確認済み。

## 追記2：ユーザーグローバル設定への同意フラグ追加

上記だけでも承認ダイアログが出たため、`~/.claude/settings.json`（新規作成）に
`skipDangerousModePermissionPrompt: true`を追加した。bypassPermissionsモード使用時の
「本当に使いますか」という同意ダイアログを、既に承諾済みとして記録するためのフラグ。

## 追記3：真因は「権限モードは会話開始時に一度だけ確定する」だった

3層すべて設定し、VSCodeの「ウィンドウの再読み込み」もしても、既存の会話ではダイアログが
出続けた。原因は、VSCode拡張の`claudeCode.initialPermissionMode`の説明にある通り、権限モードは
「新しい会話（conversation）」の開始時にのみ再解決される仕様だったため。

「ウィンドウの再読み込み」はバックエンドプロセスを再起動する（`CLAUDE_PID`は変わる）が、
既存の会話（`CLAUDE_CODE_SESSION_ID`）はそのまま再開されるため、会話開始時点で確定していた
古い権限モードを引き継いでしまっていた。

**結論**：設定変更後に有効化するには、ウィンドウの再読み込みではなく、**新しい会話を開始する**
必要がある。

## 効果が及ばない要因（設定変更では解決できないもの）

- Claude自身の「取り消し困難／外部公開を伴う操作は確認する」という振る舞い方針
- CLAUDE.mdの自律実行方針が「プロジェクトフォルダ内」に限定されている点（プロジェクト外への操作は別途判断）
- VSCode拡張独自のUI（差分承認パネル等）が別途介在する可能性
- Claudeが真にユーザー判断が必要と考えて`AskUserQuestion`を使うケース

## 追記4：2026-08-13再確認（別会話での確認プロンプト再発）

`uv run pytest`実行時に「Allow this bash command?」ダイアログが表示されたとの報告があり再点検した。

- 3層の設定（プロジェクト`.claude/settings.json`、グローバル`~/.claude/settings.json`、VSCode `claudeCode.allowDangerouslySkipPermissions`）は全て健在で、`managed-settings.json`による上書きも引き続き無し。
- 一方、**この確認を行った会話自体では**同種のbashコマンド（`git log`, `cat`, `uv run pytest`等）を確認なしで複数回実行できており、bypassは機能していた。
- 上記「追記3」の結論（権限モードは会話開始時に一度だけ確定する）と整合的。報告されたダイアログは、設定変更が反映される前に開始されていた別の会話で発生したものと推定される。対処は同じく「新しい会話を開始する」。

### 次に疑うべき別レイヤー（未確認・要調査）

上記対処後も再発する場合、`permissions`とは独立した**サンドボックス機構**（`sandbox.enabled` / `sandbox.autoAllowBashIfSandboxed`等、Bashツールの`dangerouslyDisableSandbox`パラメータに対応）が別途確認を要求している可能性がある。現時点ではプロジェクト・グローバルどちらの設定にも`sandbox`キーは存在せずデフォルト状態のため今回の原因ではないが、再発時の調査候補として記録する。
