
# pyproject.tomlまとめ

## 1. scenario_test

C:\Users\cihi1\Documents\scenario_test\pyproject.toml

[project]
name = "scenario-test"
version = "0.1.0"
requires-python = "~=3.11.0"

dependencies = [
    "orchestrator",
    "usb-camera-adapter",
]

[tool.uv]
package = false

[tool.uv.workspace]
members = [
    "orchestrator",
    "adapters/usb_camera_adapter",
]

[tool.uv.sources]
orchestrator = { workspace = true }
usb-camera-adapter = { workspace = true }


## 2. orchestrator

C:\Users\cihi1\Documents\scenario_test\orchestrator\pyproject.toml

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "orchestrator"
version = "0.1.0"
requires-python = "~=3.11.0"
dependencies = [
    "loguru>=0.7.3",
    "pytest>=9.1.1",
]

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.uv.sources]
usb-camera-adapter = { workspace = true }

## 3. adapters/usb_camera_adapter

C:\Users\cihi1\Documents\scenario_test\adapters\usb_camera_adapter\pyproject.toml

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "usb-camera-adapter"
version = "0.1.0"
requires-python = "~=3.11.0"
dependencies = [
    "loguru>=0.7.3",
    "numpy>=2.4.6",
    "opencv-python>=5.0.0.93",
    "pytest>=9.1.1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/camera_adapter", "src/camera_controller"]

## 補足

editable = true は、ソースコードの変更を再インストールなしでリアルタイムに反映させるための「開発用リンク機能」
uv のワークスペース（sources = { workspace = true }）では、デフォルトで自動的に編集可能（editable）な状態でリンクしてくれる


