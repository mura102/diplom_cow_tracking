import os
import re
from datetime import datetime

import cv2
import joblib
import numpy as np
import torch
import torch.nn as nn
from ultralytics import YOLO

from database.database import SessionLocal
from database.models import BCSMeasurement, BCSSession, Cow
from database.migrate_bcs import migrate_bcs_schema

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BASE_DIR)
# Детектор коровы — та же модель, что в модуле активности (cow_eat.pt)
DETECTOR_PATH = os.getenv(
    "DETECTOR_PATH",
    os.path.join(_PROJECT_ROOT, "external_activity", "models", "cow_eat.pt"),
)
NUMBER_MODEL_PATH = os.getenv(
    "NUMBER_MODEL_PATH", os.path.join(_BASE_DIR, "models", "best_number_classifier.pt")
)
REGRESSOR_PATH = os.getenv(
    "REGRESSOR_PATH", os.path.join(_BASE_DIR, "models", "bcs_regressor.pth")
)
SCALER_PATH = os.getenv("SCALER_PATH", os.path.join(_BASE_DIR, "models", "scaler.pkl"))

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

_pipeline = None


class BCSRegressor(nn.Module):
    def __init__(self, input_dim=5):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze()


def extract_features(cow_img):
    """Вектор из 5 признаков для регрессора BCS."""
    gray = cv2.cvtColor(cow_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return np.zeros(5)
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)
    rect = cv2.minAreaRect(cnt)
    w, h = rect[1]
    length = max(w, h)
    width = min(w, h)
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)
    solidity = area / hull_area if hull_area > 0 else 0
    compactness = area / (perimeter ** 2) if perimeter > 0 else 0
    fill_ratio = area / (length * width) if length * width > 0 else 0
    aspect_ratio = width / length if length > 0 else 0
    return np.array([aspect_ratio, compactness, solidity, fill_ratio, perimeter / length])


def default_logger(msg: str):
    print(msg)


def _resolve_cow_uuid(db, recognized_tag):
    """Связывает распознанный номер бирки с записью в таблице cows."""
    if not recognized_tag:
        return None
    if recognized_tag.isdigit():
        cow = db.query(Cow).filter(Cow.cow_number == int(recognized_tag)).first()
        if cow:
            return cow.id_cow
    cow = db.query(Cow).filter(Cow.tag_number == recognized_tag).first()
    return cow.id_cow if cow else None


class BCSPipeline:
    """Загружает модели один раз и используется для изображений и видео."""

    def __init__(self, conf=0.5, logger=default_logger):
        self.conf = conf
        self.logger = logger
        logger("[BCS] Загрузка моделей детектора, классификатора ID и регрессора...")
        self.detector = YOLO(DETECTOR_PATH)
        self.number_model = YOLO(NUMBER_MODEL_PATH)
        self.regressor = BCSRegressor()
        self.regressor.load_state_dict(torch.load(REGRESSOR_PATH, map_location="cpu"))
        self.regressor.eval()
        self.scaler = joblib.load(SCALER_PATH)
        logger(f"[BCS] Модели загружены. Классы номеров: {self.number_model.names}")

    def get_cow_id(self, cow_img):
        results = self.number_model(cow_img, conf=self.conf)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return None
        best_box = max(boxes, key=lambda b: b.conf[0])
        cls_id = int(best_box.cls[0])
        class_name = self.number_model.names[cls_id].lower()
        if class_name in WORD_TO_DIGIT:
            return WORD_TO_DIGIT[class_name]
        digits = re.findall(r"\d+", class_name)
        if digits:
            return digits[0]
        return str(cls_id + 1)

    def predict_bcs(self, cow_img):
        feat = extract_features(cow_img).reshape(1, -1)
        feat_scaled = self.scaler.transform(feat)
        feat_t = torch.tensor(feat_scaled, dtype=torch.float32)
        with torch.no_grad():
            bcs = self.regressor(feat_t).item()
        return round(max(1.0, min(5.0, bcs)), 1)

    @staticmethod
    def draw_label(frame, x1, y1, x2, y2, label, height):
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
        )
        text_x = x1
        text_y = y2 + text_h + 5
        if text_y + baseline > height:
            text_y = y2 - 5
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            frame, label, (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
        )

    def process_detection(self, frame, boxes_data, frame_idx=None):
        height = frame.shape[0]
        records = []
        for i, box in enumerate(boxes_data):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0].item())
            cow_img = frame[y1:y2, x1:x2]
            if cow_img.size == 0:
                continue

            recognized_tag = self.get_cow_id(cow_img)
            if recognized_tag is None:
                recognized_tag = str(i + 1)
            cow_number = int(recognized_tag) if recognized_tag.isdigit() else i + 1

            bcs = self.predict_bcs(cow_img)
            label = f"ID:{recognized_tag} BCS:{bcs}"
            self.draw_label(frame, x1, y1, x2, y2, label, height)

            records.append({
                "cow_id": recognized_tag,
                "cow_number": cow_number,
                "confidence": conf,
                "bcs": bcs,
                "bbox": (x1, y1, x2, y2),
                "frame": frame_idx,
            })
            self.logger(
                f"[BCS] Корова ID {recognized_tag}: BCS = {bcs} "
                f"(уверенность детекции {conf:.2f})"
            )
        return records


def get_pipeline(conf=0.5, logger=default_logger, force_reload=False):
    global _pipeline
    if _pipeline is None or force_reload:
        _pipeline = BCSPipeline(conf=conf, logger=logger)
    return _pipeline


def _save_to_db(
    records,
    *,
    image_path=None,
    video_path=None,
    source_type="image",
    session_cow_id=None,
    stream_id=None,
    logger=default_logger,
):
    if not records and source_type == "image":
        records = []

    db = SessionLocal()
    try:
        migrate_bcs_schema()
        session = BCSSession(
            id_cow=session_cow_id,
            id_stream=stream_id,
            start_time=datetime.utcnow(),
            image_path=image_path or "",
            video_path=video_path,
            source_type=source_type,
            num_cows_detected=len({r["cow_id"] for r in records}) if records else 0,
        )
        db.add(session)
        db.flush()

        for rec in records:
            bbox = rec.get("bbox")
            bbox_str = (
                f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}" if bbox else None
            )
            recognized_tag = rec.get("cow_id")
            linked_cow = _resolve_cow_uuid(db, recognized_tag) or session_cow_id
            measurement = BCSMeasurement(
                id_session=session.id,
                id_cow=linked_cow,
                recognized_tag=recognized_tag,
                cow_number=rec.get("cow_number"),
                bcs_value=rec["bcs"],
                confidence=rec["confidence"],
                bbox_coords=bbox_str,
                frame_number=rec.get("frame"),
                created_at=datetime.utcnow(),
            )
            db.add(measurement)

        db.commit()
        logger(f"[BCS] Сессия BCS сохранена в БД (id={session.id})")
        return session.id
    except Exception as e:
        db.rollback()
        logger(f"[BCS] Ошибка при сохранении BCS в БД: {e}")
        raise
    finally:
        db.close()


def predict_bcs_all(
    image_path: str,
    cow_id=None,
    stream_id=None,
    save_result_image: bool = True,
    result_image_path: str = "bcs_result.jpg",
    logger=default_logger,
    conf: float = 0.5,
    use_db: bool = True,
):
    """
    Обрабатывает изображение: детекция коров, ID по бирке, BCS, запись в PostgreSQL.
    Совместим с интерфейсом PyQt6 (BcsWindow).
    """
    if use_db:
        migrate_bcs_schema()

    pipeline = get_pipeline(conf=conf, logger=logger)

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Не удалось загрузить изображение: {image_path}")

    results = pipeline.detector(img, conf=conf)
    boxes_data = results[0].boxes
    if boxes_data is None or len(boxes_data) == 0:
        logger("[BCS] Коров не обнаружено на изображении.")
        return img, []

    logger(f"[BCS] Обнаружено коров: {len(boxes_data)}")
    records = pipeline.process_detection(img, boxes_data, frame_idx=None)

    if save_result_image:
        cv2.imwrite(result_image_path, img)
        logger(f"[BCS] Размеченное изображение сохранено как {result_image_path}")

    if use_db:
        _save_to_db(
            records,
            image_path=image_path,
            source_type="image",
            session_cow_id=cow_id,
            stream_id=stream_id,
            logger=logger,
        )

    return img, records


def process_video(
    video_path: str,
    output_path: str = "output_video.mp4",
    cow_id=None,
    stream_id=None,
    conf: float = 0.5,
    skip_frames: int = 1,
    use_db: bool = True,
    logger=default_logger,
):
    """Обрабатывает видео: детекция, ID, BCS, опционально запись в PostgreSQL."""
    if use_db:
        migrate_bcs_schema()

    pipeline = get_pipeline(conf=conf, logger=logger)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Не удалось открыть видео: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps / skip_frames, (width, height))

    frame_idx = 0
    processed_frames = 0
    all_records = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % skip_frames != 0:
                frame_idx += 1
                continue

            results = pipeline.detector(frame, conf=conf)
            boxes = results[0].boxes
            if boxes is not None and len(boxes) > 0:
                records = pipeline.process_detection(frame, boxes, frame_idx=frame_idx)
                all_records.extend(records)

            out.write(frame)
            processed_frames += 1
            frame_idx += 1

            if processed_frames % 30 == 0:
                logger(f"[BCS] Обработано кадров: {processed_frames} / {total_frames}")
    finally:
        cap.release()
        out.release()

    logger(f"[BCS] Видео сохранено: {output_path}")

    if use_db:
        _save_to_db(
            all_records,
            video_path=os.path.abspath(video_path),
            source_type="video",
            session_cow_id=cow_id,
            stream_id=stream_id,
            logger=logger,
        )

    return output_path, all_records


def analyze_bcs(image_path: str, cow_id=None, stream_id=None, logger=default_logger):
    """Точка входа без сохранения размеченного изображения."""
    return predict_bcs_all(
        image_path=image_path,
        cow_id=cow_id,
        stream_id=stream_id,
        save_result_image=False,
        logger=logger,
    )[1]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Анализ BCS коров с распознаванием ID")
    parser.add_argument("--mode", choices=["image", "video"], default="image")
    parser.add_argument("--input", "-i", help="Путь к изображению или видео")
    parser.add_argument("--output", "-o", default="bcs_result.jpg")
    parser.add_argument("--conf", type=float, default=0.5)
    parser.add_argument("--skip-frames", type=int, default=1)
    parser.add_argument("--no-db", action="store_true")
    args = parser.parse_args()
    use_db = not args.no_db

    if args.mode == "video":
        if not args.input:
            raise SystemExit("Укажите --input для видео")
        process_video(
            args.input,
            output_path=args.output if args.output.endswith(".mp4") else "output_video.mp4",
            conf=args.conf,
            skip_frames=args.skip_frames,
            use_db=use_db,
        )
    else:
        input_path = args.input or os.path.join(_BASE_DIR, "models", "tests", "sample.jpg")
        _, data = predict_bcs_all(
            input_path,
            result_image_path=args.output,
            conf=args.conf,
            use_db=use_db,
        )
        print("\nИтоговые данные:")
        for d in data:
            print(
                f"ID {d['cow_id']}: BCS={d['bcs']}, "
                f"уверенность={d['confidence']:.2f}"
            )
