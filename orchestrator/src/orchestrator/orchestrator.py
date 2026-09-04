from loguru import logger
import yaml

from adapter_core.baseadapter import BaseAdapter
from adapter_core.logging_utils import summarize_result
from orchestrator.context import Context
from orchestrator.registry import load_adapter_class, validate_pipeline


class GenericOrchestrator:

    def __init__(self, config_path: str | None = None):
        """config_pathはexecute_pipeline()（YAMLファイル経由）を使う場合のみ必要。
        既にパース済みのpipelineを直接渡すexecute()を使う場合は不要。
        """
        self.config_path = config_path
        self.context = Context()  # execute()実行後、ここに各ステップの結果が貯まる

    async def execute_pipeline(self) -> bool:
        """self.config_pathのYAMLファイルを読み込んでから実行する（従来の外部インターフェース）。

        ファイルを読む部分だけをここに残し、実行ロジック本体はexecute()に委譲する。
        """
        if self.config_path is None:
            logger.error("execute_pipeline()の呼び出しにはconfig_pathの指定が必要です。")
            return False

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            logger.exception(f"YAML ファイルの読み込みに失敗しました: {e}")
            return False

        pipeline = config.get("pipeline", [])
        return await self.execute(pipeline)

    async def execute(self, pipeline: list[dict]) -> bool:
        """既にパース済みのpipeline（list[dict]）を直接実行する。

        normalizer.converter.convert()の戻り値をそのまま渡せる（ファイル書き出し不要）。
        setup/teardown（with構文）はsyncのまま。execute_stepだけawaitする。

        pipelineの各要素は以下の2形式のどちらかを取る：
        - 従来形式（1要素=1アクション）: {"adapter", "action", "params"}
            paramsはコンストラクタとexecute_stepの両方に渡る
        - steps形式（1要素=同一インスタンスでの複数アクション）: {"adapter", "params", "steps": [...]}
            paramsはコンストラクタ専用。各steps[i]が{"action", "params"}を持ち、
            同じAdapterインスタンス（setup/teardownは1回だけ）に対して順番にexecute_stepされる

        各execute_stepの結果はself.contextに記録される（呼び出し側は実行後に参照できる）。
        呼び出しのたびにself.contextはリセットされる（前回実行の履歴を引きずらない）。

        実行前に全ステップのadapterクラスパスを一括検証する（registry.validate_pipeline）。
        1つでも不正なら、何も実行せずにFalseを返す（実行途中で発覚して一部だけ実行済み、
        という事故を防ぐ）。
        """
        self.context = Context()

        errors = validate_pipeline(pipeline)
        if errors:
            for error in errors:
                logger.error(f"[事前検証エラー] {error}")
            return False

        logger.info(f"パイプライン実行開始 (全 {len(pipeline)} ステップ)")

        for step_info in pipeline:
            step_name = step_info.get("name", "Unknown Step")
            class_path = step_info.get("adapter")
            params = step_info.get("params", {})
            sub_steps = step_info.get("steps")

            logger.info(f"--- Step: {step_name} ---")

            try:
                # 1. クラスの動的ロードとインスタンス化（同一インスタンスを以下で使い回す）
                #    事前検証済みだが、ロード自体はここで改めて行う（sys.modulesキャッシュ済みで軽量）
                cls = load_adapter_class(class_path)
                adapter: BaseAdapter = cls(config=params)

                # 2. BaseAdapter に集約した with 構文（setup / teardown）を利用して安全に実行！
                #    setup/teardownは1回だけ。steps形式なら中で複数回execute_stepする
                with adapter:
                    if sub_steps is not None:
                        for sub_step in sub_steps:
                            action = sub_step.get("action")
                            sub_params = sub_step.get("params", {})
                            result = await adapter.execute_step(
                                action=action, params=sub_params
                            )
                            logger.info(
                                f"[{step_name}] {action} 実行結果: {summarize_result(result)}"
                            )
                            self.context.record(name=step_name, action=action, result=result)
                    else:
                        action = step_info.get("action")
                        result = await adapter.execute_step(action=action, params=params)
                        logger.info(f"[{step_name}] 実行結果: {summarize_result(result)}")
                        self.context.record(name=step_name, action=action, result=result)

            except Exception as e:
                logger.exception(
                    f"[{step_name}] ステップ実行中にエラーが発生しました: {e}"
                )
                return False

        return True
