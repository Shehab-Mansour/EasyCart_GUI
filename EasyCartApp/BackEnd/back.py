import json
import os
from urllib.parse import unquote

class ProductManager:
    def __init__(self):
        base = os.path.dirname(__file__)
        self.json_path = os.path.join(base, "product.json")
        self.media_path = os.path.join(base, "media")
        self.products = self._load()

    def _load(self):
        with open(self.json_path, encoding='utf-8') as f:
            return json.load(f)

    def get_product_by_qr(self, qr):
        return next((p for p in self.products if p["QRNumber"] == str(qr)), None)

    def get_product_image_path(self, qr):
        p = self.get_product_by_qr(qr)
        if not p: return None
        rel = unquote(p["ProductImage"].replace("/media/", ""))
        path = os.path.join(self.media_path, rel)
        return path if os.path.exists(path) else None
