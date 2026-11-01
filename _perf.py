import time
import threading
from collections import defaultdict

from config import PERF_LOGGING

class Perf:
    def __init__(self, interval=5.0, tag="perf"):
        self.interval = interval
        self.tag = tag
        self._lock = threading.Lock()
        self._t0 = time.perf_counter()
        self._cnt = defaultdict(int)
        self._sum = defaultdict(float)
        self._n = defaultdict(int)
        self._max = defaultdict(float)

    def count(self, name, k=1):
        with self._lock:
            self._cnt[name] += k

    def add(self, name, seconds):
        ms = seconds * 1000.0
        with self._lock:
            self._sum[name] += ms
            self._n[name] += 1
            if ms > self._max[name]:
                self._max[name] = ms

    def report_if_due(self):
        now = time.perf_counter()
        with self._lock:
            dt = now - self._t0
            if dt < self.interval:
                return
            parts = [f"{k} {v / dt:.1f}/s" for k, v in sorted(self._cnt.items())]
            parts += [
                f"{k} avg {self._sum[k] / self._n[k]:.1f} max {self._max[k]:.1f} ms"
                for k in sorted(self._sum)
            ]
            self._cnt.clear()
            self._sum.clear()
            self._n.clear()
            self._max.clear()
            self._t0 = now
        
        if PERF_LOGGING: 
            print(f"[{self.tag}] " + " | ".join(parts), flush=True)


perf = Perf()