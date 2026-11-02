import cv2
import queue
import subprocess
import numpy as np
from config import SCREEN_WIDTH, SCREEN_HEIGHT, IS_LINUX

import time #[p]
from utils.perf import perf #[p]

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

def cam_loop(app_buffer):
    # mreow
    yolo_q_input = app_buffer.yolo_q_input

    frame_state = app_buffer.frame_state
    frame_lock = app_buffer.frame_lock

    stop_event = app_buffer.camera_stop

    # local
    frame_idx = 0
    log_file = None
    
    with frame_lock:
        frame_state['frame_idx'] = 0
    
    if IS_LINUX:
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
        while not stop_event.is_set():
            yolo_active = frame_state.get('yolo_enabled', False)

            # get GUI frame
            if IS_LINUX:
                t_read = time.perf_counter() #[p]

                raw = proc.stdout.read(frame_size)

                perf.add('cam_read', time.perf_counter() - t_read) #[p]

                if len(raw) < frame_size:
                    print(f"rpicam-vid err: {proc.poll()}. check logs!")
                    break

                t_work = time.perf_counter() #[p]
                yuv = np.frombuffer(raw, dtype=np.uint8).reshape((SCREEN_HEIGHT * 3 // 2, SCREEN_WIDTH))
                
                t_convert = time.perf_counter() #[p]
                f_rgb = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB_I420)
                perf.add('cam_rgb', time.perf_counter() - t_convert) #[p]

            else:
                t_read = time.perf_counter() #[p]
                ok, f_bgr = cap.read()
                perf.add('cam_read', time.perf_counter() - t_read) #[p]
                if not ok: 
                    break
                
                t_work = time.perf_counter() #[p]
                t_convert = time.perf_counter() #[p]
                
                f_rgb = cv2.cvtColor(f_bgr, cv2.COLOR_BGR2RGB)
                
                perf.add('cam_rgb', time.perf_counter() - t_convert) #[p]     

            # post converted YOLO frame
            if yolo_active:
                if yolo_q_input.full():
                    perf.count('yolo_drop') #[p]
                
                else:
                    t_yolo = time.perf_counter() #[p]
                    f_raw = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420) if IS_LINUX else f_bgr
                    perf.add('cam_bgr', time.perf_counter() - t_yolo) #[p]
                    # f_yolo = cv2.resize(f_raw, (320, 200), interpolation=cv2.INTER_LINEAR)

                    try:
                        t_put = time.perf_counter() #[p]
                        yolo_q_input.put(f_raw, block=False)
                        perf.add('cam_queue_put', time.perf_counter() - t_put) #[p]
                        perf.count('yolo_send') #[p]

                    except queue.Full:
                        perf.count('yolo_drop') #[p]

            frame_idx += 1
            with frame_lock:
                frame_state['frame'] = f_rgb
                frame_state['frame_idx'] = frame_idx

            #[p]
            perf.add('cam_work', time.perf_counter() - t_work)
            perf.count('cam_frames')
            perf.report_if_due()
            #[p]

    finally:
        if IS_LINUX: 
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
            log_file.close()
            
        else: 
            cap.release()
        
        print("camera stopped")
