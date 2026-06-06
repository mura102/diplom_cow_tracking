"""Чтение/запись изображений OpenCV с путями Unicode (Windows)."""

import os

import cv2
import numpy as np


def imread_unicode(path: str):
    if not path or not os.path.isfile(path):
        return None
    try:
        data = np.fromfile(path, dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return cv2.imread(path)


def imwrite_unicode(path: str, image) -> bool:
    if image is None:
        return False
    ext = os.path.splitext(path)[1] or ".jpg"
    try:
        ok, encoded = cv2.imencode(ext, image)
        if ok:
            encoded.tofile(path)
            return True
    except Exception:
        pass
    return cv2.imwrite(path, image)
