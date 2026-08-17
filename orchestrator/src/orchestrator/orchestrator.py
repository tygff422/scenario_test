from loguru import logger


class Orchestrator:
    def __init__(self, adapter=None):
        if adapter is None:
            from camera_adapter.camera_adapter import CameraAdapter
            self.adapter = CameraAdapter()
        else:
            self.adapter = adapter
    
    def execute(self) -> bool:
        logger.info("デバイスの検査を開始")
        try:
            with self.adapter as adapter:
                status = adapter.check_device_status()
                logger.info(f"検査結果: {status}")

                if status == "READY":
                    return True
                else:
                    logger.error("デバイスの準備ができてないから、処理を中断...")
                    return False
        except Exception as e:
            logger.exception(f"Error発生")
            return False


import importlib
from typing import Type
from loguru import logger
import yaml

from adapter_core.baseadapter import BaseAdapter


class GenericOrchestrator:

    def __init__(self, config_path: str):
        self.config_path = config_path

    def _load_adapter(self, class_path: str) -> Type[BaseAdapter]:
        """文字列からクラスを動的にロードし、BaseAdapter の派生クラスか検証する"""
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)

        # 抽出したクラスが本当に BaseAdapter を継承しているか厳格にチェック！
        if not issubclass(cls, BaseAdapter):
            raise TypeError(
                f"{class_name} は BaseAdapter を継承していません。"
            )
        return cls

    async def execute_pipeline(self) -> bool:
        """YAML に定義されたステップを順番に実行する

        setup/teardown（with構文）はsyncのまま。execute_stepだけawaitする。
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            logger.exception(f"YAML ファイルの読み込みに失敗しました: {e}")
            return False

        pipeline = config.get("pipeline", [])
        logger.info(f"パイプライン実行開始 (全 {len(pipeline)} ステップ)")

        for step_info in pipeline:
            step_name = step_info.get("name", "Unknown Step")
            class_path = step_info.get("adapter")
            action = step_info.get("action")
            params = step_info.get("params", {})

            logger.info(f"--- Step: {step_name} ---")

            try:
                # 1. クラスの動的ロードとインスタンス化
                cls = self._load_adapter(class_path)
                adapter: BaseAdapter = cls(config=params)

                # 2. BaseAdapter に集約した with 構文（setup / teardown）を利用して安全に実行！
                with adapter:
                    result = await adapter.execute_step(action=action, params=params)
                    logger.info(f"[{step_name}] 実行結果: {result}")

            except Exception as e:
                logger.exception(
                    f"[{step_name}] ステップ実行中にエラーが発生しました: {e}"
                )
                return False

        return True
