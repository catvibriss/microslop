import cv2
import queue
from config import SCREEN_WIDTH, SCREEN_HEIGHT, CAMERA_WIDTH, CAMERA_HEIGHT

def cam_loop(q_in, buffer_container, video_buffer_lock):
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    real_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    real_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"camera ready. camera size: {int(real_w)}x{int(real_h)}")

    while cap.isOpened():
        ok, f_bgr = cap.read()
        if not ok: 
            break
            
        try: 
            q_in.put(f_bgr, block=False)   
        except queue.Full: 
            pass
            
        f_resized = cv2.resize(f_bgr, (SCREEN_WIDTH, SCREEN_HEIGHT), interpolation=cv2.INTER_AREA)
        f_rgb = cv2.cvtColor(f_resized, cv2.COLOR_BGR2RGB)
        
        with video_buffer_lock:
            buffer_container['frame'] = f_rgb.copy()
            
    cap.release()
    print("camera closed")
