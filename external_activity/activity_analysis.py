"""
Модуль детекции активности коровы (еда / питьё).
Автор: Рената. Адаптирован для ERP "Рога и копыта".

Изменения v3:
  1. Ленивая загрузка YOLO через _get_detector()
  2. Добавлен progress_callback для проброса логов в UI
  3. Совместим с вызовом из AnalysisWorker
  4. Безопаснее обрабатывает ошибки загрузки кадров и БД
  5. Выводит количество обнаруженных объектов на кадре
  6. Рисует bbox + уверенность + метку состояния через cv2 (без PIL, без ???????)
  7. Сохраняет размеченные кадры в output_dir/{run_time}/
  8. Пишет confidence в таблицу frames (если колонка есть), иначе fallback
"""

import cv2
import datetime
import os
from pathlib import Path
from ultralytics import YOLO

from external_activity.db_config import get_connection, get_default_cow_number

_BASE_DIR     = Path(__file__).parent
DETECTOR_PATH = str(_BASE_DIR / "models" / "cow_eat.pt")
INTERVAL_SEC  = 5
_detector     = None

# Цвета для состояний (BGR для OpenCV)
_STATE_COLORS = {
    "питание":    (0,   200,   0),   # зелёный
    "питье":      (255, 140,   0),   # синий
    "неизвестно": (0,   200, 255),   # жёлтый
}
_COLOR_NO_COW  = (80, 80, 80)        # серый — корова не найдена

# Латинские метки для cv2 (кириллица не поддерживается cv2.putText)
_STATE_LABELS = {
    "питание":    "FEED",
    "питье":      "DRINK",
    "неизвестно": "COW",
}


def _get_detector() -> YOLO:
    global _detector
    if _detector is None:
        if not os.path.exists(DETECTOR_PATH):
            raise FileNotFoundError(f"Файл модели не найден: {DETECTOR_PATH}")
        _detector = YOLO(DETECTOR_PATH)
    return _detector


def _log(message: str, progress_callback=None):
    print(message)
    if progress_callback:
        try:
            progress_callback(message)
        except Exception:
            pass


def _draw_annotated_frame(img, boxes, state: str, cow_count: int):
    """
    Рисует на кадре через cv2 (без PIL):
      - Цветную рамку bbox вокруг каждой коровы
      - Метку состояния + уверенность над рамкой
      - Плашку с количеством объектов в левом верхнем углу
    Возвращает новый размеченный кадр.
    """
    out          = img.copy()
    color        = _STATE_COLORS.get(state, _COLOR_NO_COW)
    action_label = _STATE_LABELS.get(state, "COW")

    if boxes is not None and len(boxes) > 0:
        for idx, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])

            # Рамка вокруг объекта
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 3)

            # Метка: "#1 FEED 0.87"
            label = f"#{idx + 1} {action_label} {conf:.2f}"
            (lw, lh), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1
            )
            label_y = max(y1 - 10, lh + 10)

            # Фон под текстом
            cv2.rectangle(
                out,
                (x1, label_y - lh - 8),
                (x1 + lw + 8, label_y + 4),
                color, -1,
            )
            cv2.putText(
                out, label,
                (x1 + 4, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 0, 0), 1, cv2.LINE_AA,
            )

    # Счётчик объектов — плашка в левом верхнем углу
    counter = f"Objects: {cow_count}"
    (cw, ch), _ = cv2.getTextSize(counter, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(out, (8, 8), (cw + 24, ch + 24), (0, 0, 0), -1)
    cv2.putText(
        out, counter,
        (16, ch + 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55, (255, 255, 255), 1, cv2.LINE_AA,
    )

    return out


def process_sequence(
    image_paths,
    camera_locations,
    cow_number,
    interval_sec=INTERVAL_SEC,
    show_frames=False,
    save_frames=True,
    output_dir="feed_frames",
    progress_callback=None,
):
    """
    Обрабатывает список снимков, определяет состояние коровы и пишет в БД.

    Возвращает:
        (total_feed_sec: float, total_drink_sec: float)
    """
    if not image_paths:
        raise ValueError("Список image_paths пуст")

    if isinstance(camera_locations, str):
        camera_locations = [camera_locations] * len(image_paths)
    elif len(camera_locations) != len(image_paths):
        raise ValueError(
            "Длина camera_locations должна совпадать с количеством изображений"
        )

    # Папка для размеченных кадров
    annotated_dir = None
    if save_frames:
        run_time      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        annotated_dir = os.path.join(output_dir, run_time)
        os.makedirs(annotated_dir, exist_ok=True)

    detector = _get_detector()
    _log(f"YOLO загружена: {DETECTOR_PATH}", progress_callback)

    conn   = get_connection()
    cursor = conn.cursor()

    try:
        start_time_iso = datetime.datetime.now().isoformat()
        cursor.execute(
            """INSERT INTO sessions
                   (cow_number, start_time, total_duration_feed_sec,
                    total_duration_drink_sec, num_frames)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (cow_number, start_time_iso, 0.0, 0.0, len(image_paths)),
        )
        session_id = cursor.fetchone()[0]
        conn.commit()

        _log(f"=== СЕССИЯ {session_id} (корова №{cow_number}) ===", progress_callback)
        _log(f"Интервал между кадрами: {interval_sec} сек", progress_callback)
        _log(f"Всего кадров: {len(image_paths)}", progress_callback)

        total_feed_sec     = 0.0
        total_drink_sec    = 0.0
        active_feed_start  = None
        active_drink_start = None

        for i, (img_path, cam_loc) in enumerate(zip(image_paths, camera_locations)):
            current_time = i * interval_sec
            img = cv2.imread(img_path)
            if img is None:
                _log(
                    f"[{current_time:.0f} сек] Ошибка загрузки {img_path}",
                    progress_callback,
                )
                continue

            results      = detector(img, verbose=False)
            boxes        = results[0].boxes
            cow_count    = len(boxes) if boxes is not None else 0
            cow_detected = cow_count > 0

            # Средняя уверенность
            avg_conf = (
                float(sum(b.conf[0] for b in boxes) / cow_count)
                if cow_detected and boxes is not None
                else 0.0
            )

            if cow_detected:
                if cam_loc == "кормушка":
                    state = "питание"
                elif cam_loc == "поилка":
                    state = "питье"
                else:
                    state = "неизвестно"
            else:
                state = None

            # Обновляем таймеры активности
            if cow_detected:
                if state == "питание":
                    if active_feed_start is None:
                        active_feed_start = current_time
                    if active_drink_start is not None:
                        duration = current_time - active_drink_start
                        total_drink_sec += duration
                        _log(f"   Питьё завершено, длительность: {duration:.1f} сек", progress_callback)
                        active_drink_start = None
                elif state == "питье":
                    if active_drink_start is None:
                        active_drink_start = current_time
                    if active_feed_start is not None:
                        duration = current_time - active_feed_start
                        total_feed_sec += duration
                        _log(f"   Питание завершено, длительность: {duration:.1f} сек", progress_callback)
                        active_feed_start = None
            else:
                if active_feed_start is not None:
                    duration = current_time - active_feed_start
                    total_feed_sec += duration
                    _log(f"   Питание завершено, длительность: {duration:.1f} сек", progress_callback)
                    active_feed_start = None
                if active_drink_start is not None:
                    duration = current_time - active_drink_start
                    total_drink_sec += duration
                    _log(f"   Питьё завершено, длительность: {duration:.1f} сек", progress_callback)
                    active_drink_start = None

            _log(
                f"[{current_time:.0f} сек] "
                f"Объектов: {cow_count} | "
                f"Уверенность: {avg_conf:.2f} | "
                f"Камера: {cam_loc} | "
                f"Состояние: {state or '—'}",
                progress_callback,
            )

            # Размеченный кадр
            annotated_path = None
            if show_frames or save_frames:
                annotated = _draw_annotated_frame(img, boxes, state or "", cow_count)

                if show_frames:
                    cv2.imshow("Activity Analysis", annotated)
                    cv2.waitKey(1)

                if save_frames and annotated_dir:
                    fname          = f"frame_{i:03d}_t{int(current_time)}s_obj{cow_count}.jpg"
                    annotated_path = os.path.join(annotated_dir, fname)
                    cv2.imwrite(annotated_path, annotated)
                    _log(f"   💾 Кадр сохранён: {fname}", progress_callback)

            saved_img_path = annotated_path if annotated_path else img_path

            # INSERT в frames — с confidence если колонка есть, иначе fallback
            try:
                cursor.execute(
                    """INSERT INTO frames
                           (session_id, timestamp_sec, cow_detected,
                            state, camera_location, image_path, confidence)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (session_id, current_time, cow_detected,
                     state, cam_loc, saved_img_path, avg_conf),
                )
                conn.commit()
            except Exception as insert_err:
                conn.rollback()
                _log(
                    f"[frames] confidence не записан ({type(insert_err).__name__}), "
                    "сохраняю без confidence",
                    progress_callback,
                )
                cursor.execute(
                    """INSERT INTO frames
                           (session_id, timestamp_sec, cow_detected,
                            state, camera_location, image_path)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (session_id, current_time, cow_detected,
                     state, cam_loc, saved_img_path),
                )
                conn.commit()

        # Закрываем незакрытые интервалы
        last_time = (len(image_paths) - 1) * interval_sec
        if active_feed_start is not None:
            duration = last_time - active_feed_start + interval_sec
            total_feed_sec += duration
            _log(f"Питание продолжалось до конца, добавлено {duration:.1f} сек", progress_callback)
        if active_drink_start is not None:
            duration = last_time - active_drink_start + interval_sec
            total_drink_sec += duration
            _log(f"Питьё продолжалось до конца, добавлено {duration:.1f} сек", progress_callback)

        cursor.execute(
            """UPDATE sessions
               SET total_duration_feed_sec  = %s,
                   total_duration_drink_sec = %s
               WHERE id = %s""",
            (total_feed_sec, total_drink_sec, session_id),
        )
        conn.commit()

        _log(f"✅ Питание : {total_feed_sec:.1f} сек ({total_feed_sec / 60:.2f} мин)", progress_callback)
        _log(f"✅ Питьё   : {total_drink_sec:.1f} сек ({total_drink_sec / 60:.2f} мин)", progress_callback)
        if save_frames and annotated_dir:
            _log(f"📁 Размеченные кадры: {annotated_dir}", progress_callback)

        return total_feed_sec, total_drink_sec

    finally:
        cursor.close()
        conn.close()
        if show_frames:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    cow_number = get_default_cow_number()
    print(f"Работаем с коровой №{cow_number}")

    frame_paths = [
        "tests/eat1.jpg",
        "tests/eat1.jpg",
        "tests/no.jpg",
        "tests/eat1.jpg",
        "tests/no.jpg",
        "tests/eat1.jpg",
    ]
    camera_locations = [
        "кормушка", "кормушка", "поилка",
        "поилка",   "кормушка", "кормушка",
    ]
    process_sequence(
        frame_paths,
        camera_locations,
        cow_number,
        interval_sec=5,
        show_frames=False,
        save_frames=True,
        output_dir="feed_frames",
    )
