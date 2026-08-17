import importlib

import pytest


@pytest.mark.hardware
def test_dynamic_import_camera_adapter():
    class_path = "camera_adapter.camera_adapter.CameraAdapter"
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    adapter = cls()
    print(f"Loaded Class: {cls}")
    print(f"Setup Result: {adapter.setup()}")
    adapter.teardown()

