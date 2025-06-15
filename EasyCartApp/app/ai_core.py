import threading
import time
import serial
import json
from PIL import Image
from AI.object_detector import ObjectDetector
from BackEnd.back import ProductManager


class EasyCartAICore:
    def __init__(self, on_product_confirmed, on_product_removed):
        # Serial and AI state
        self.serial_data = {"weight": 0.0, "ultrasonic": [100, 100, 100, 100], "position": [0, 0]}
        self.weight_offset = None
        self.last_weights = []

        # Logic thresholds
        self.required_samples = 1
        self.margin = 15.0
        self.required_seen_count = 10
        self.detection_distance_cm = 20
        self.detection_hold_seconds = 50
        self.confirmation_hold_time = 1.0
        self.stable_weight_window = 2.0

        # Detection state
        self.pending_product = None
        self.pending_since = None
        self.stable_start_weight = None

        self.pending_removed_product = None
        self.removal_since = None
        self.removal_start_weight = None

        # AI and state
        self.detector = ObjectDetector(confidence_threshold=0.85)
        self.product_manager = ProductManager()

        self.running = True
        self.ai_active = True  # Control AI detection
        self.detection_active = False
        self.delay_timer = None

        self.waiting_products = []  # Hidden
        self.confirmed_products = []
        self.seen_products = {}

        # External handlers
        self.on_product_confirmed = on_product_confirmed
        self.on_product_removed = on_product_removed

        # Monitoring state
        self.monitoring_active = False
        self.last_known_weight = None

        # Start background
        threading.Thread(target=self.read_serial_loop, daemon=True).start()
        threading.Thread(target=self.weight_processing_loop, daemon=True).start()
        threading.Thread(target=self.main_loop, daemon=True).start()
        threading.Thread(target=self.monitor_weight_loop, daemon=True).start()

    def stop_detection(self):
        self.ai_active = False
        self.detector.stop()
        print("[AI Core] Detection manually stopped.")
        self.last_known_weight = self.serial_data.get("weight", 0.0)
        self.monitoring_active = True

    def resume_detection(self):
        self.ai_active = True
        self.monitoring_active = False
        print("[AI Core] Detection manually resumed.")

    def read_serial_loop(self):
        try:
            ser = serial.Serial("/dev/ttyAMA0", 921600, timeout=1)
            print("[AI] Serial connected")
        except Exception as e:
            print(f"[AI] Serial failed: {e}")
            return

        while True:
            try:
                line = ser.readline().decode().strip()
                if not line:
                    continue
                data = json.loads(line)

                if self.weight_offset is None:
                    self.weight_offset = data.get("weight", 0.0)

                weight = data.get("weight", 0.0) - self.weight_offset
                self.last_weights.append(weight)
                if len(self.last_weights) > self.required_samples:
                    self.last_weights.pop(0)

                avg_weight = sum(self.last_weights) / len(self.last_weights)
                data["weight"] = avg_weight if len(self.last_weights) >= self.required_samples else 0.0
                self.serial_data = data

            except json.JSONDecodeError:
                print("[AI] JSON error")
            except Exception as e:
                print(f"[AI] Serial error: {e}")

    def main_loop(self):
        while self.running:
            if not self.ai_active:
                time.sleep(0.2)
                continue

            distances = self.serial_data.get("ultrasonic", [100] * 4)
            if any(d != -1 and d < self.detection_distance_cm for d in distances):
                if not self.detection_active:
                    self.detection_active = True
                    self.detector.start(self.on_detect, None)
                    print("[AI] Object detected, starting detection")
                self.delay_timer = None
            else:
                if self.detection_active:
                    if not self.delay_timer:
                        self.delay_timer = time.time()
                    elif time.time() - self.delay_timer > self.detection_hold_seconds:
                        self.detector.stop()
                        self.detection_active = False
                        print("[AI] Object left, stopping detection")
                        self.delay_timer = None
            time.sleep(0.1)

    def on_detect(self, products):
        for product in products:
            name = product.get("ProductName")
            self.seen_products[name] = self.seen_products.get(name, 0) + 1
            if self.seen_products[name] >= self.required_seen_count:
                if not any(p.get("ProductName") == name for p in self.waiting_products):
                    self.waiting_products.append(product)
                    print(f"[AI] Added to waiting: {name}")

    def get_confirmed_total_weight(self):
        return sum(float(p.get("ProductWeight", 0)) for p in self.confirmed_products)

    def weight_processing_loop(self):
        while True:
            if len(self.last_weights) < self.required_samples:
                time.sleep(0.1)
                continue

            if not self.ai_active:
                time.sleep(0.1)
                continue

            now = time.time()
            current = self.serial_data.get("weight", 0.0)
            confirmed_total = self.get_confirmed_total_weight()
            diff = round(current - confirmed_total, 2)

            # Add product
            if self.pending_product is None:
                for product in self.waiting_products:
                    expected = float(product.get("ProductWeight", 0))
                    if abs(current - (confirmed_total + expected)) <= self.margin:
                        self.pending_product = product
                        self.pending_since = now
                        self.stable_start_weight = current
                        print(f"[AI] Monitoring confirm: {product['ProductName']}")
                        break
            else:
                expected = float(self.pending_product.get("ProductWeight", 0))
                target = confirmed_total + expected
                if abs(current - self.stable_start_weight) <= self.stable_weight_window and abs(current - target) <= self.margin:
                    if now - self.pending_since >= self.confirmation_hold_time:
                        name = self.pending_product.get("ProductName")
                        self.confirmed_products.append(self.pending_product)
                        self.waiting_products.remove(self.pending_product)
                        print(f"[AI] Confirmed: {name}")
                        self.on_product_confirmed(self.pending_product)
                        self.pending_product = None
                        self.pending_since = None
                else:
                    self.pending_product = None
                    self.pending_since = None

            # Remove product
            if self.pending_removed_product is None and diff < 0:
                for product in self.confirmed_products:
                    expected = float(product.get("ProductWeight", 0))
                    if abs(abs(diff) - expected) <= self.margin:
                        self.pending_removed_product = product
                        self.removal_since = now
                        self.removal_start_weight = current
                        print(f"[AI] Monitoring remove: {product['ProductName']}")
                        break
            elif self.pending_removed_product:
                expected = float(self.pending_removed_product.get("ProductWeight", 0))
                target = confirmed_total - expected
                if abs(current - self.removal_start_weight) <= self.stable_weight_window and abs(current - target) <= self.margin:
                    if now - self.removal_since >= self.confirmation_hold_time:
                        name = self.pending_removed_product.get("ProductName")
                        self.confirmed_products.remove(self.pending_removed_product)
                        print(f"[AI] Removed: {name}")
                        self.on_product_removed(self.pending_removed_product)
                        self.pending_removed_product = None
                        self.removal_since = None
                else:
                    self.pending_removed_product = None
                    self.removal_since = None

            time.sleep(0.1)

    def monitor_weight_loop(self):
        while True:
            if not self.monitoring_active or self.last_known_weight is None:
                time.sleep(0.2)
                continue

            current = self.serial_data.get("weight", 0.0)
            if abs(current - self.last_known_weight) > self.margin:
                print("[WARNING] Weight changed outside margin! Please return product or adjust.")
                while abs(current - self.last_known_weight) > self.margin:
                    time.sleep(0.2)
                    current = self.serial_data.get("weight", 0.0)
                print("[INFO] Weight is stable again.")
            time.sleep(0.2)
