import sys
import os
import cv2
import queue
import subprocess
import numpy as np
from config import SCREEN_WIDTH, SCREEN_HEIGHT

import time #[p]
from _perf import perf #[p]

def start_rpicam():
    log_file = open("logs/rpicam.log", "wb")
    cmd = [
        'rpicam-vid', 
        '--width', str(SCREEN_WIDTH), 
        '--height', str(SCREEN_HEIGHT),
        '--codec', 'yuv420', 
        '--timeout', '0', 
        '--nopreview', 
        '-o', '-',     
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=log_file, stdin=subprocess.DEVNULL)
    return proc, log_file

def cam_loop(q_in, buffer_container, video_buffer_lock):
    use_rpicam = sys.platform.startswith('linux')

    frame_idx = 0
    log_file = None
    
    with video_buffer_lock:
        buffer_container['frame_idx'] = 0
    
    if use_rpicam:
        proc, log_file = start_rpicam()
        frame_size = SCREEN_WIDTH * SCREEN_HEIGHT * 3 // 2
        print(f"[camera] rpicam-vid. res: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    else: # windows tests
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_HEIGHT)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        proc = None
        print(f"[camera] openCV. res: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    try:
        while True:
            yolo_active = buffer_container.get('yolo_enabled', False)

            if use_rpicam:
                raw = proc.stdout.read(frame_size)
                if len(raw) < frame_size:
                    print(f"rpicam-vid err: {proc.poll()}. check logs!")
                    break

                t_work = time.perf_counter() #[p]
                
                yuv = np.frombuffer(raw, dtype=np.uint8).reshape((SCREEN_HEIGHT * 3 // 2, SCREEN_WIDTH))
                
                f_rgb = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB_I420)

            else:
                ok, f_bgr = cap.read()
                if not ok: 
                    break
                
                t_work = time.perf_counter() #[p]
                
                f_rgb = cv2.cvtColor(f_bgr, cv2.COLOR_BGR2RGB)     

            if yolo_active:

                if q_in.full():
                    perf.count('yolo_drop') #[p]
                
                else:
                    f_yolo = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420) if use_rpicam else f_bgr
                    try:
                        q_in.put(f_yolo, block=False)

                        perf.count('yolo_send') #[p]

                    except queue.Full:
                        perf.count('yolo_drop') #[p]

            frame_idx += 1
            with video_buffer_lock:
                buffer_container['frame'] = f_rgb
                buffer_container['frame_idx'] = frame_idx

            #[p]
            perf.add('cam_work', time.perf_counter() - t_work)
            perf.count('cam_frames')
            perf.report_if_due()
            #[p]

    finally:
        if use_rpicam: 
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()

        else: 
            cap.release()
        
        print("camera stopped")
