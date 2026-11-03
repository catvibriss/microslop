# declaration
from enum import Enum, auto

class AppMode(Enum):
    CLEAR = auto()
    CAMERA = auto()
    YOLO = auto()
    EDUCATION = auto()
    SETTINGS = auto()

# UI basics
from .base import ModeBasic

# actual pages
from .yolo import YoloMode
from .camera import CameraMode

# result
MODES_CLASSES = {
    AppMode.CLEAR: ModeBasic,
    AppMode.CAMERA: CameraMode,
    AppMode.YOLO: YoloMode,
    AppMode.EDUCATION: ModeBasic,
    AppMode.SETTINGS: ModeBasic
}
