import time
import cv2

def process_camera(picam, index, detector, active_flag, queue, show_camera):
    while True:
        frame = picam.capture_array()
        if active_flag[0]:
            confirmed_ids = detector.detect_and_confirm(frame)
            if confirmed_ids:
                for class_id in confirmed_ids:
                    queue.append(class_id)

        if show_camera[0]:
            cv2.imshow(f"Camera {index}", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                show_camera[0] = False
                cv2.destroyWindow(f"Camera {index}")

        time.sleep(0.01)