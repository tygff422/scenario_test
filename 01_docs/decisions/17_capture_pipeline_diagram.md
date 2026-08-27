# 17_capture_pipeline_diagram

- 日付: 2026-08-27
- 関連: [16_normalizer_puml_folder.md](16_normalizer_puml_folder.md)
- ステータス: 完了

## 背景

変換・実行経路をClaudeのArtifact機能で図にしたところ好評だったため、後から見返せるように残す方法を検討した。

## 検討した選択肢

| 案 | 内容 |
|---|---|
| A | Mermaid図をmarkdownに埋め込む（GitHubでそのまま表示される） |
| B | このHTMLファイルをそのまま`01_docs/`に保存する |
| C | ArtifactのURLをdocsにメモとして残すだけ |

## 決定：B（HTMLファイルをdocsに保存）を採用

`01_docs/capture_pipeline_map.html`として保存した。見た目（配色・フォント・SVG図）をそのまま残せることを優先。

VSCode拡張「Live Preview」（`ms-vscode.live-server`）を導入し、VSCode内でこのHTMLをプレビュー表示できるようにした。

**注意**：このファイルはClaudeのArtifact機能向けに書かれたページ本体（`<title>`/`<style>`/コンテンツ）のみで、`<!DOCTYPE>`・`<html>`・`<head>`・`<body>`タグを持たない。Artifact上では自動的にこれらで包まれて表示される。ブラウザ・Live Previewで直接開いた場合はブラウザ側の暗黙補完に依存するため、表示が崩れる場合は`<!DOCTYPE html><html><head>...</head><body>...</body></html>`で明示的に包み直す対応が必要になる可能性がある。

**参考（バックアップ）**：見た目重視で見たい場合は、ClaudeのArtifactとしても公開済み（アカウント依存・非公開）。URLは会話履歴を参照。

## 今後

内容が古くなった場合、Claudeに再度図を作らせて`01_docs/capture_pipeline_map.html`を上書きする運用とする。
