import time
import numpy as np
import onnxruntime as ort

PATH = "models/v6_960/best.onnx"
RUNS = 10

def bench_ort(threads):
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    t = time.perf_counter()
    sess = ort.InferenceSession(PATH, so, providers=["CPUExecutionProvider"])
    t_load = time.perf_counter() - t

    inp = sess.get_inputs()[0]
    shape = list(inp.shape)
    if not all(isinstance(d, int) for d in shape):
        shape = [1, 3, 320, 320]
    x = np.random.rand(*shape).astype(np.float32)

    for _ in range(2):
        sess.run(None, {inp.name: x})
    times = []
    for _ in range(RUNS):
        t = time.perf_counter()
        sess.run(None, {inp.name: x})
        times.append((time.perf_counter() - t) * 1000)
    print(f"[ORT] threads={threads} input={inp.shape} used={shape} "
          f"load={t_load:.2f}s avg={sum(times) / RUNS:.0f}ms min={min(times):.0f}ms", flush=True)

def bench_ultralytics():
    from ultralytics import YOLO
    t = time.perf_counter()
    m = YOLO(PATH)
    print(f"[ULTRA] YOLO(): {time.perf_counter() - t:.2f}s", flush=True)

    frame = np.zeros((800, 1280, 3), np.uint8)
    t = time.perf_counter()
    m.predict(frame, imgsz=320, verbose=False, device="cpu")
    print(f"[ULTRA] first predict: {time.perf_counter() - t:.2f}s", flush=True)

    times = []
    for _ in range(RUNS):
        t = time.perf_counter()
        m.predict(frame, imgsz=320, verbose=False, device="cpu")
        times.append((time.perf_counter() - t) * 1000)
    print(f"[ULTRA] steady: avg={sum(times) / RUNS:.0f}ms min={min(times):.0f}ms", flush=True)

if __name__ == "__main__":
    for th in (1, 2, 3, 4):
        bench_ort(th)
    bench_ultralytics()