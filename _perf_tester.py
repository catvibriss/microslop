import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
TESTS = [
    ('baseline_clear_480_t2', 'CLEAR', 480, 2),
    ('yolo_480_t2', 'YOLO', 480, 2),
    ('yolo_320_t2', 'YOLO', 320, 2),
    ('yolo_480_t1', 'YOLO', 480, 1),
    ('yolo_480_t2_repeat', 'YOLO', 480, 2),
]

def throttle():
    try:
        p = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True,
                           text=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 'unavailable'

def get_rate(line, name):
    match = re.search(r'\b' + re.escape(name) + r'\s+([0-9.]+)/s', line)
    return float(match.group(1)) if match else None

def collect(log_path):
    data = {key: [] for key in ['cam_frames','ui_new_frames','ui_ticks','infer_done']}
    active = False
    for line in log_path.read_text(errors='replace').splitlines():
        if '[TEST START]' in line:
            active = True
            continue
        if '[TEST END]' in line:
            active = False
        if not active:
            continue
        for key in data:
            value = get_rate(line, key)
            if value is not None:
                data[key].append(value)
    return {f'{key}_avg': round(mean(values),2) if values else None
            for key, values in data.items()}

def run_one(name, mode, imgsz, threads, seconds, folder):
    env = os.environ.copy()
    env.update({
        'MICROSLOP_TEST_MODE': mode,
        'MICROSLOP_TEST_IMGSZ': str(imgsz),
        'MICROSLOP_TEST_SECONDS': str(seconds),
        'YOLO_THREADS': str(threads),
        'PYTHONUNBUFFERED': '1',
    })
    path = folder / f'{name}.log'
    print(f'\n[tester] {name}: mode={mode} imgsz={imgsz} threads={threads} seconds={seconds}', flush=True)
    before = throttle()
    with path.open('w', encoding='utf-8') as log:
        proc = subprocess.Popen([sys.executable, '-u', 'app.py'], cwd=ROOT,
                                env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            ret = proc.wait(timeout=seconds + 150)
        except subprocess.TimeoutExpired:
            print('[tester] TIMEOUT: terminate', flush=True)
            proc.terminate()
            try:
                ret = proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                ret = proc.wait()
    after = throttle()
    content = path.read_text(errors='replace')
    ok = ret == 0 and '[TEST START]' in content and '[TEST END]' in content
    row = dict(test=name, mode=mode, imgsz=imgsz, threads=threads,
               duration_s=seconds, exit_code=ret, completed=ok,
               throttle_before=before, throttle_after=after,
               log=str(path.relative_to(ROOT)), **collect(path))
    print(f'[tester] result: {"OK" if ok else "FAILED"}; '
          f'GUI={row["ui_new_frames_avg"]} FPS; '
          f'cam={row["cam_frames_avg"]} FPS; '
          f'YOLO={row["infer_done_avg"]} FPS',flush=True)
    return row

def main():
    ap = argparse.ArgumentParser(description='Automated microslop performance tests')
    ap.add_argument('--quick', action='store_true', help='короткий прогон для проверки автоматизации')
    ap.add_argument('--seconds', type=int, default=45, help='длительность каждого теста YOLO')
    args = ap.parse_args()
    if args.seconds < 5:
        ap.error('--seconds должен быть >=5')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = ROOT / 'perf_runs' / stamp
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, mode, imgsz, threads in TESTS:
        duration = (12 if mode == 'CLEAR' else 20) if args.quick else (35 if mode == 'CLEAR' else args.seconds)
        rows.append(run_one(name, mode, imgsz, threads, duration, folder))
        (folder / 'summary.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
        with (folder / 'summary.csv').open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    print(f'\n[tester] reports: {folder}', flush=True)
    print('[tester] Failed runs:', sum(not r['completed'] for r in rows), flush=True)

if __name__ == '__main__':
    main()
