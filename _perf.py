import os
import time
import threading
from collections import defaultdict, deque

import config

try:
    import psutil
except ImportError:
    psutil = None

class Perf:
    def __init__(self, interval=5.0, tag="perf", samples=256):
        self.interval = interval
        self.tag = tag
        self.samples = samples
        self._lock = threading.Lock()
        self._t0 = time.perf_counter()
        self._cnt = defaultdict(int)
        self._sum = defaultdict(float)
        self._n = defaultdict(int)
        self._max = defaultdict(float)
        self._values = defaultdict(lambda: deque(maxlen=self.samples))
        self._pid = os.getpid()
        self._proc = None
        if psutil is not None:
            self._init_process()

    @property
    def enabled(self):
        return bool(getattr(config, 'PERF_LOGGING', True))

    def _init_process(self):
        self._proc = psutil.Process(os.getpid())
        self._proc.cpu_percent(None)
        if self.tag == 'perf':
            psutil.cpu_percent(interval=None, percpu=True)

    def count(self, name, k=1):
        if not self.enabled:
            return
        with self._lock:
            self._cnt[name] += k

    def add(self, name, seconds):
        if not self.enabled:
            return
        ms = seconds * 1000.0
        with self._lock:
            self._sum[name] += ms
            self._n[name] += 1
            self._max[name] = max(self._max[name], ms)
            self._values[name].append(ms)

    def report_if_due(self):
        if not self.enabled:
            return
        now = time.perf_counter()
        with self._lock:
            dt = now - self._t0
            if dt < self.interval:
                return
            parts = [f"{k} {v / dt:.1f}/s" for k, v in sorted(self._cnt.items())]
            for k in sorted(self._sum):
                vals = sorted(self._values[k])
                p95 = vals[min(len(vals) - 1, int(0.95 * (len(vals) - 1)))]
                parts.append(
                    f"{k} avg {self._sum[k] / self._n[k]:.1f} "
                    f"p95 {p95:.1f} max {self._max[k]:.1f} ms"
                )
            self._cnt.clear()
            self._sum.clear()
            self._n.clear()
            self._max.clear()
            self._values.clear()
            self._t0 = now

        if psutil is not None:
            if self._pid != os.getpid():
                self._pid = os.getpid()
                self._init_process()
            try:
                if self._proc is None:
                    self._init_process()
                parts.append(f"cpu {self._proc.cpu_percent(None):.0f}%")
                parts.append(f"rss {self._proc.memory_info().rss / 1048576:.1f}MiB")
                if self.tag == 'perf':
                    usage = psutil.cpu_percent(interval=None, percpu=True)
                    parts.append('cores ' + ','.join(f'{v:.0f}%' for v in usage))
            except (psutil.Error, OSError):
                pass

        print(f"[{self.tag}] " + " | ".join(parts), flush=True)


perf = Perf()