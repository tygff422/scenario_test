import importlib
from typing import Type

from adapter_core.baseadapter import BaseAdapter


def load_adapter_class(class_path: str) -> Type[BaseAdapter]:
    """文字列からクラスを動的にロードし、BaseAdapterの派生クラスか検証する。

    GenericOrchestratorの各ステップ実行時と、validate_pipeline()の事前検証の
    両方から呼ばれる共通ロジック。
    """
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    if not issubclass(cls, BaseAdapter):
        raise TypeError(f"{class_name} は BaseAdapter を継承していません。")
    return cls


def validate_pipeline(pipeline: list[dict]) -> list[str]:
    """pipeline内の全adapterクラスパスをロードできるか、実行前に一括で検証する。

    インスタンス化やsetup/execute_stepは行わない（クラスがロードできるかだけ見る）。
    戻り値はエラーメッセージのlist。空リストなら全て正常。
    """
    errors: list[str] = []

    for step_info in pipeline:
        step_name = step_info.get("name", "Unknown Step")
        class_path = step_info.get("adapter")

        if not class_path:
            errors.append(f"[{step_name}] adapterが指定されていません。")
            continue

        try:
            load_adapter_class(class_path)
        except Exception as e:
            errors.append(f"[{step_name}] {class_path} のロードに失敗しました: {e}")

    return errors
