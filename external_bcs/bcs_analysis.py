import cv2
import numpy as np
import joblib
import torch
import torch.nn as nn
from ultralytics import YOLO
from datetime import datetime

from database.database import SessionLocal
from database.models import BCSSession, BCSMeasurement


# Пути к моделям (подстрой под свою структуру проекта)
DETECTOR_PATH = "external_bcs/models/best_cow_detector.pt"
REGRESSOR_PATH = "external_bcs/models/bcs_regressor.pth"
SCALER_PATH = "external_bcs/models/scaler.pkl"


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
    gray = cv2.cvtColor(cow_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
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
    last_feature = perimeter / length if length > 0 else 0

    return np.array(
        [aspect_ratio, compactness, solidity, fill_ratio, last_feature]
    )


def default_logger(msg: str):
    """Логгер по умолчанию — просто печать в консоль."""
    print(msg)


def predict_bcs_all(
    image_path: str,
    cow_id=None,
    stream_id=None,
    save_result_image: bool = True,
    result_image_path: str = "bcs_result.jpg",
    logger=default_logger,
):
    """
    Главная функция, которая:
      1) считает BCS по изображению;
      2) создаёт BCS-сессию и измерения в твоей БД;
      3) пишет лог через logger (GUI или консоль).

    В БД используются модели:
      - BCSSession
      - BCSMeasurement
    """

    # Загрузка моделей
    logger("[BCS] Загрузка моделей детектора и регрессора...")
    detector = YOLO(DETECTOR_PATH)

    regressor = BCSRegressor()
    regressor.load_state_dict(
        torch.load(REGRESSOR_PATH, map_location="cpu")
    )
    regressor.eval()

    scaler = joblib.load(SCALER_PATH)

    # Чтение изображения
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Не удалось загрузить изображение: {image_path}")

    # Детекция коров
    results = detector(img)
    boxes_data = results[0].boxes

    if boxes_data is None or len(boxes_data) == 0:
        logger("[BCS] Коров не обнаружено на изображении.")
        return img, []

    logger(f"[BCS] Обнаружено коров: {len(boxes_data)}")

    records = []
    for i, box in enumerate(boxes_data):
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = box.conf[0].item()

        cow_img = img[y1:y2, x1:x2]
        if cow_img.size == 0:
            continue

        feat = extract_features(cow_img).reshape(1, -1)
        feat_scaled = scaler.transform(feat)
        feat_t = torch.tensor(feat_scaled, dtype=torch.float32)

        with torch.no_grad():
            bcs = regressor(feat_t).item()

        # ограничиваем диапазон 1..5 и округляем
        bcs = round(max(1.0, min(5.0, bcs)), 1)
        cow_number = i + 1

        # рисуем на изображении
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            img,
            f"BCS {bcs}",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            3,
            (0, 255, 0),
            3,
        )

        records.append(
            {
                "cow_number": cow_number,
                "confidence": conf,
                "bcs": bcs,
                "bbox": (x1, y1, x2, y2),
            }
        )
        logger(
            f"[BCS] Корова #{cow_number}: BCS = {bcs} (уверенность {conf:.2f})"
        )

    # Сохраняем размеченное изображение
    if save_result_image:
        cv2.imwrite(result_image_path, img)
        logger(f"[BCS] Размеченное изображение сохранено как {result_image_path}")

    # Записываем результаты в твою БД
    db = SessionLocal()
    try:
        session = BCSSession(
            id_cow=cow_id,
            id_stream=stream_id,
            start_time=datetime.utcnow(),
            image_path=image_path,
            num_cows_detected=len(records),
        )
        db.add(session)
        db.flush()  # получаем session.id

        for rec in records:
            bbox = rec.get("bbox")
            bbox_str = (
                f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}" if bbox else None
            )
            measurement = BCSMeasurement(
                id_session=session.id,
                id_cow=cow_id,
                bcs_value=rec["bcs"],
                confidence=rec["confidence"],
                bbox_coords=bbox_str,
                created_at=datetime.utcnow(),
            )
            db.add(measurement)

        db.commit()
        logger(f"[BCS] Сессия BCS сохранена в БД (id={session.id})")
    except Exception as e:
        db.rollback()
        logger(f"[BCS] Ошибка при сохранении BCS в БД: {e}")
    finally:
        db.close()

    return img, records


def analyze_bcs(image_path: str, cow_id=None, stream_id=None, logger=default_logger):
    """
    Удобная точка входа для твоей системы.
    Возвращает список records, параллельно пишет в БД.
    """
    _, records = predict_bcs_all(
        image_path=image_path,
        cow_id=cow_id,
        stream_id=stream_id,
        save_result_image=False,
        logger=logger,
    )
    return records


if __name__ == "__main__":
    # Пример самостоятельного запуска, как у Стаса.
    test_image = "external_bcs/models/tests/20260228_112352.jpg"
    img, data = predict_bcs_all(
        image_path=test_image,
        cow_id=None,
        stream_id=None,
        save_result_image=True,
        result_image_path="bcs_result.jpg",
    )
    print("\nИтоговые данные:")
    for d in data:
        print(
            f"Корова №{d['cow_number']}: BCS={d['bcs']}, "
            f"уверенность={d['confidence']:.2f}"
        )