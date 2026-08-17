# 09_async_execute_step

- 日付: 2026-08-17
- 関連Step: Step5（非同期化） / [implementation_plan.md](../implementation_plan.md) 14-4「asyncとsyncの境界」
- ステータス: 完了

## 背景

学習計画（Phase4・14-4）には非同期化の境界方針が既に明記されていた。

```text
Orchestrator:          async
Adapter.execute:       async
Adapter.connect/disconnect: sync
Controller:             sync
境界: asyncio.to_thread
```

これに沿って実プロジェクトの`GenericOrchestrator`/`BaseAdapter`/`CameraAdapter`を非同期化した。

## 決定・変更内容

### 境界は`execute_step`のみ

`setup()`/`teardown()`（＝`with`構文、connect/disconnect相当）はsyncのまま変更しない。async化するのは`execute_step`とそれを呼ぶ`GenericOrchestrator.execute_pipeline`だけ。

### 変更したファイル

| ファイル | 変更内容 |
|---|---|
| `adapter_core/baseadapter.py` | `execute_step`の抽象メソッド定義を`async def`に変更 |
| `camera_adapter/camera_adapter.py` | `execute_step`を`async def`化。`camera_controller.set_resolution`/`capture`の呼び出しを`asyncio.to_thread`でラップしブロッキングを分離 |
| `orchestrator/orchestrator.py` | `GenericOrchestrator.execute_pipeline`を`async def`化。`with adapter:`（sync）はそのまま、内側の`adapter.execute_step(...)`だけ`await`する |
| `orchestrator/tests/orchestrator_test_support/fake_pipeline_adapter.py` | `FakePipelineAdapter.execute_step`を`async def`化（`BaseAdapter`の契約に合わせる） |
| `orchestrator/tests/test_generic_orchestrator.py` | `execute_pipeline()`の呼び出し7箇所を`asyncio.run(orchestrator.execute_pipeline())`でラップ |
| `orchestrator/README.md` | 使用例を`asyncio.run(...)`に更新 |

### 対象外としたもの（決定）

デモ用の`Orchestrator`（`CameraAdapter`固定クラス）は今回async化しない。`execute_step`を経由せず`check_device_status()`を直接呼ぶ構造のため影響を受けず、本線は`GenericOrchestrator`である以上そちらを優先した。将来デモ用クラス側にも非同期対応が必要になれば別途検討する。

### テストの非同期対応方針

`pytest-asyncio`は追加せず、`asyncio.run()`で同期テスト関数の中から呼び出す方式を採用（依存を増やさないシンプルな方法。テストは1関数につき1つのコルーチンを実行するだけなので、非同期fixture等が必要になるまではこれで十分）。

## 確認

`uv sync` → 成功。`uv run pytest -m "not hardware" -q` → `14 passed, 2 deselected`（修正前と同じ、退行なし）。
