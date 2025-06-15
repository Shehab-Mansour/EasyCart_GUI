from ultralytics import YOLO
from picamera2 import Picamera2
import threading
import cv2
from BackEnd.back import ProductManager

class ObjectDetector:
    def __init__(self, confidence_threshold=0.8, show_camera=False):
        self.model = YOLO("AI/best2_ncnn_model")
        self.class_map = {
            0: 300, 1: 301, 2: 302,
            3: 303, 4: 304, 5: 305,
            6: 306, 7: 307, 8: 308, 9: 309
        }

        self.cam = Picamera2(1)
        self.cam.preview_configuration.main.size = (416, 416)
        self.cam.preview_configuration.main.format = "RGB888"
        self.cam.preview_configuration.align()
        self.cam.configure("preview")
        self.cam.start()

        self.product_manager = ProductManager()
        self.running = False
        self.confidence = confidence_threshold
        self.show_camera = show_camera
        self.on_detect = None
        self.on_camera = None
        self.counts = {}

    def start(self, on_detect, on_camera):
        self.running = True
        self.on_detect = on_detect
        self.on_camera = on_camera
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            frame = self.cam.capture_array()

            # ??? ????????
            if self.on_camera:
                self.on_camera(frame)

            results = self.model.predict(frame, verbose=False, show=False)

            detected_products = []

            for result in results:
                for box in result.boxes:
                    conf = float(box.conf)
                    if conf < self.confidence:
                        continue

                    class_id = int(box.cls)
                    if class_id in self.class_map:
                        qr = self.class_map[class_id]
                        product = self.product_manager.get_product_by_qr(qr)
                        if product:
                            product["ProductImagePath"] = self.product_manager.get_product_image_path(qr)
                            self.counts[qr] = self.counts.get(qr, 0) + 1
                            product["SeenCount"] = self.counts[qr]
                            detected_products.append(product)

            if self.on_detect and detected_products:
                self.on_detect(detected_products)
