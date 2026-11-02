from .const import *
from .manager import SETTINGS

import os
import sys
IS_LINUX = sys.platform.startswith('linux')

YOLO_IMGSZ = int(os.environ.get('MICROSLOP_TEST_IMGSZ', YOLO_IMGSZ))