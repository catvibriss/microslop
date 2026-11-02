from pathlib import Path

import numpy as np

from config import *

import time #[p]
from utils.perf import perf #[p]

def worker(yolo_q_input, yolo_q_result, yolo_q_status):
    print(f"\n[yolo] imgsz: {YOLO_IMGSZ}\n")

    # YOLO speed эксперименты
    if IS_LINUX:
        import os
        nice = int(os.environ.get("YOLO_NICE", YOLO_NICE))
        thr = int(os.environ.get("YOLO_THREADS", YOLO_THREADS))

        if nice:
            os.nice(nice)

        if thr:
            import onnxruntime as ort
            _orig = ort.InferenceSession

            class _Sess(_orig):
                def __init__(self, path, sess_options=None, providers=None, **kw):
                    if sess_options is None:
                        sess_options = ort.SessionOptions()
                    sess_options.intra_op_num_threads = thr
                    super().__init__(path, sess_options=sess_options, providers=providers, **kw)

            ort.InferenceSession = _Sess

        print(f"[yolo] tune: nice={nice} threads={thr}", flush=True)

    # -- -- -- -- --

    from ultralytics import YOLO

    t_boot = time.perf_counter() #[p]
    perf.tag = 'yolo' #[p]

    try:
        # model_path = Path("models") / "v6_960" / "best.pt"
        model_path = Path("models") / "v6_960" / "best.onnx"
        target_device = "cpu"

        m = YOLO(str(model_path))

        # prewarm
        print("[yolo] prewarm: start")
        _f_fake = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)

        for i in range(3):
            t_warm = time.perf_counter() #[p]

            m.predict(_f_fake, verbose=False, device=target_device, imgsz=YOLO_IMGSZ)

            print(f"[yolo] prewarm: predict #{i} {(time.perf_counter() - t_warm)*1000:.0f} ms") #[p]

        yolo_q_status.put("READY")
        print(f"[yolo] start -> READY: {time.perf_counter() - t_boot:.2f} s", flush=True) #[p]

    except Exception as e:
        yolo_q_status.put(f"[yolo] startup error: {e}")
        return

    n = 0  #[p]

    while True:
        try:
            t_wait = time.perf_counter() #[p]
            f = yolo_q_input.get()
            perf.add('yolo_queue_wait', time.perf_counter() - t_wait) #[p]

            if f is None:
                break

            #[p]
            t = time.perf_counter()

            results = m.predict(f, verbose=False, device=target_device, imgsz=YOLO_IMGSZ)

            dt = time.perf_counter() - t

            n += 1
            if n <= 3:
                print(f"[yolo] predict #{n}: {dt * 1000:.0f} ms", flush=True)
            perf.add('infer', dt)
            perf.count('infer_done')
            perf.report_if_due()
            #[p]

            t_post = time.perf_counter() #[p]

            r = results[0]
            out = []
            for b in r.boxes:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                cls_id = int(b.cls[0])
                conf_val = float(b.conf[0])
                out.append((x1, y1, x2, y2, r.names[cls_id], conf_val))

            perf.add('yolo_postprocess', time.perf_counter() - t_post) #[p]
            t_put = time.perf_counter() #[p]

            yolo_q_result.put(out)

            perf.add('yolo_result_put', time.perf_counter() - t_put) #[p]

        except Exception:
            break
