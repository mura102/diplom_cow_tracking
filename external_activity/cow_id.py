"""Распознавание ID коровы по бирке (YOLO-классификатор из модуля BCS)."""

import os
import re
from pathlib import Path

from ultralytics import YOLO

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
NUMBER_MODEL_PATH = os.getenv(
    "NUMBER_MODEL_PATH",
    str(_PROJECT_ROOT / "external_bcs" / "models" / "best_number_classifier.pt"),
)

WORD_TO_DIGIT = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
}

_recognizer = None


def _parse_class_name(class_name: str) -> str:
    name = class_name.lower()
    if name in WORD_TO_DIGIT:
        return WORD_TO_DIGIT[name]
    digits = re.findall(r"\d+", name)
    if digits:
        return digits[0]
    return name


class CowIDRecognizer:
    def __init__(self, conf: float = 0.5):
        if not os.path.exists(NUMBER_MODEL_PATH):
            raise FileNotFoundError(
                f"Модель классификатора ID не найдена: {NUMBER_MODEL_PATH}"
            )
        self.conf = conf
        self.model = YOLO(NUMBER_MODEL_PATH)

    def recognize_crop(self, cow_img, fallback: str | None = None) -> str | None:
        if cow_img is None or cow_img.size == 0:
            return fallback
        results = self.model(cow_img, conf=self.conf, verbose=False)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return fallback
        best_box = max(boxes, key=lambda b: b.conf[0])
        cls_id = int(best_box.cls[0])
        class_name = self.model.names[cls_id]
        return _parse_class_name(class_name) or fallback

    def recognize_from_boxes(self, img, boxes, fallback: str = "1") -> str:
        if boxes is None or len(boxes) == 0:
            return fallback
        best = max(boxes, key=lambda b: float(b.conf[0]) * (
            (float(b.xyxy[0][2]) - float(b.xyxy[0][0]))
            * (float(b.xyxy[0][3]) - float(b.xyxy[0][1]))
        ))
        x1, y1, x2, y2 = map(int, best.xyxy[0])
        crop = img[y1:y2, x1:x2]
        tag = self.recognize_crop(crop, fallback=None)
        return tag if tag else fallback

    def recognize_all_boxes(self, img, boxes) -> list[str]:
        if boxes is None or len(boxes) == 0:
            return []
        tags = []
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            crop = img[y1:y2, x1:x2]
            tag = self.recognize_crop(crop, fallback=str(i + 1))
            tags.append(tag or str(i + 1))
        return tags


def get_id_recognizer(conf: float = 0.5) -> CowIDRecognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = CowIDRecognizer(conf=conf)
    return _recognizer


def resolve_cow_number(recognized_tag: str | None, fallback: int) -> int:
    if recognized_tag and recognized_tag.isdigit():
        return int(recognized_tag)
    return fallback


def dominant_tag(tags: list[str]) -> str | None:
    if not tags:
        return None
    counts: dict[str, int] = {}
    for t in tags:
        counts[t] = counts.get(t, 0) + 1
    return max(counts, key=counts.get)


def unique_tags(tags: list[str]) -> list[str]:
    seen: list[str] = []
    for t in tags:
        if t and t not in seen:
            seen.append(t)
    return seen


def format_tags(tags: list[str]) -> str:
    unique = unique_tags(tags)
    return ", ".join(unique) if unique else "—"
