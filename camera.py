import sys
import os
import cv2
import queue
import subprocess
import numpy as np
from config import SCREEN_WIDTH, SCREEN_HEIGHT

def update_hardware_zoom(proc, zoom_factor):
    if proc is None or proc.poll() is not None:
        return

    if zoom_factor <= 1.0:
        roi_str = "roi 0.0,0.0,1.0,1.0\n"
    else:
        size = 1.0 / zoom_factor
        offset = (1.0 - size) / 2.0
        roi_str = f"roi {offset:.4f},{offset:.4f},{size:.4f},{size:.4f}\n"
    
    try:
        proc.stdin.write(roi_str.encode())
        proc.stdin.flush()
    except IOError:
        pass

def cam_loop(q_in, buffer_container, video_buffer_lock):
    use_rpicam = sys.platform.startswith('linux')
    
    with video_buffer_lock:
        buffer_container['zoom_factor'] = 1.0
        buffer_container['frame_idx'] = 0
    
    if use_rpicam:        
        cmd = [
            'rpicam-vid', 
            '--width', str(SCREEN_WIDTH), 
            '--height', str(SCREEN_HEIGHT),
            '--codec', 'yuv420', 
            '--timeout', '0', 
            '--nopreview', 
            '--keypress', 
            '-o', '-',     
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        update_hardware_zoom(proc, 1.0)

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

    last_zoom = 1.0

    try:
        while True:
            with video_buffer_lock:
                current_zoom = buffer_container.get('zoom_factor', 1.0)
                yolo_active = buffer_container.get('yolo_enabled', False)
                frame_idx = buffer_container.get('frame_idx', 0)
            
            if use_rpicam and current_zoom != last_zoom:
                update_hardware_zoom(proc, current_zoom)
                last_zoom = current_zoom

            if use_rpicam:
                raw = proc.stdout.read(frame_size)
                if len(raw) < frame_size:
                    err = proc.stderr.read().decode().strip()
                    print(f"rpicam-vid err: {err}")
                    break
                
                yuv = np.frombuffer(raw, dtype=np.uint8).reshape((SCREEN_HEIGHT * 3 // 2, SCREEN_WIDTH))
                
                f_rgb = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB_I420)
                f_yolo = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

            else:
                ok, f_bgr = cap.read()
                if not ok: 
                    break

                f_rgb = cv2.cvtColor(f_bgr, cv2.COLOR_BGR2RGB)     
                f_yolo = f_bgr.copy()                          

            if yolo_active:
                try: 
                    q_in.put(f_yolo.copy(), block=False)
                except queue.Full: 
                    pass

            with video_buffer_lock:
                buffer_container['frame'] = f_rgb.copy()
                buffer_container['frame_idx'] = (frame_idx + 1) % 10000

    finally:
        if use_rpicam: 
            proc.terminate()
        else: 
            cap.release()
        print("camera stopped")
