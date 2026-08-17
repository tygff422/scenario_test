import sys

from orchestrator.orchestrator import Orchestrator
from camera_adapter.camera_adapter import CameraAdapter
from camera_controller.camera_controller import CameraController



camera_controller = CameraController(device_id=0)
camera_adapter = CameraAdapter(camera_controller=camera_controller)
orchestrator = Orchestrator(adapter=camera_adapter)

result = orchestrator.execute()
if result:
    sys.exit(0)
else:
    sys.exit(1)
