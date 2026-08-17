from loguru import logger
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAdapter(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def setup(self) -> bool:
        pass

    @abstractmethod
    def execute_step(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def teardown(self) -> None:
        pass


# --- コンテクストマネージャーの共通化 ---
    def __enter__(self):
        if not self.setup():
            raise RuntimeError("BaseAdapter: setup() に失敗しました。")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.teardown()
        except Exception as e:
            logger.warning(f"teardown 実行中に例外が発生しました: {e}, exc_type: {exc_type}, exc_val: {exc_val}, exc_tb: {exc_tb}")
        return False
