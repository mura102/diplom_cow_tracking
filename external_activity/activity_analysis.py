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

import datetime
import os
from collections import defaultdict
from pathlib import Path

import cv2
from ultralytics import YOLO

from external_activity.activity_zone import normalize_zone, state_label, zone_to_state
from external_activity.cow_id import (
    dominant_tag,
    format_tags,
    get_id_recognizer,
    resolve_cow_number,
    unique_tags,
)
from external_activity.db_config import get_connection, get_default_cow_number
from vision.cv_io import imread_unicode, imwrite_unicode

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


def _draw_annotated_frame(img, boxes, state: str, cow_count: int, box_tags=None):
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

            tag = (box_tags[idx] if box_tags and idx < len(box_tags) else str(idx + 1))
            label = f"ID:{tag} {action_label} {conf:.2f}"
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


def _build_cow_results(
    frame_tags: list[str],
    feed_sec: dict[str, float],
    drink_sec: dict[str, float],
    fallback_cow: int,
) -> list[dict]:
    tags = unique_tags(frame_tags + list(feed_sec.keys()) + list(drink_sec.keys()))
    results = []
    for tag in tags:
        cnum = resolve_cow_number(tag, fallback_cow)
        results.append({
            "recognized_tag": tag,
            "cow_number": cnum,
            "feed_sec": feed_sec.get(tag, 0.0),
            "drink_sec": drink_sec.get(tag, 0.0),
        })
    return results


def _save_cow_results(cursor, session_id: int, cow_results: list[dict]):
    for cr in cow_results:
        cursor.execute(
            """INSERT INTO activity_cow_results
                   (session_id, recognized_tag, cow_number, feed_sec, drink_sec)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                session_id,
                cr["recognized_tag"],
                cr["cow_number"],
                cr["feed_sec"],
                cr["drink_sec"],
            ),
        )


def process_sequence(
    image_paths,
    camera_locations,
    cow_number,
    interval_sec=INTERVAL_SEC,
    show_frames=False,
    save_frames=True,
    output_dir="feed_frames",
    progress_callback=None,
    activity_zone: str | None = None,
):
    """
    Обрабатывает список снимков, определяет состояние коровы и пишет в БД.

    Возвращает:
        (total_feed_sec, total_drink_sec, session_tag, cow_results)
    """
    if not image_paths:
        raise ValueError("Список image_paths пуст")

    if activity_zone:
        zone = normalize_zone(activity_zone)
        camera_locations = [zone] * len(image_paths)
        _log(
            f"Режим теста по видео: зона «{zone}» → {state_label(zone)}",
            progress_callback,
        )
    elif isinstance(camera_locations, str):
        camera_locations = [normalize_zone(camera_locations)] * len(image_paths)
    elif len(camera_locations) != len(image_paths):
        raise ValueError(
            "Длина camera_locations должна совпадать с количеством изображений"
        )
    else:
        camera_locations = [normalize_zone(loc) for loc in camera_locations]

    # Папка для размеченных кадров
    annotated_dir = None
    if save_frames:
        run_time      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        annotated_dir = os.path.join(output_dir, run_time)
        os.makedirs(annotated_dir, exist_ok=True)

    detector = _get_detector()
    id_recognizer = get_id_recognizer()
    _log(f"YOLO загружена: {DETECTOR_PATH}", progress_callback)
    _log(f"Классификатор ID загружен", progress_callback)

    from database.migrate_activity import migrate_activity_tables

    migrate_activity_tables()

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

        frame_tags: list[str] = []
        _log(f"=== СЕССИЯ {session_id} (корова №{cow_number}) ===", progress_callback)
        _log(f"Интервал между кадрами: {interval_sec} сек", progress_callback)
        _log(f"Всего кадров: {len(image_paths)}", progress_callback)

        feed_sec_per_cow: dict[str, float] = defaultdict(float)
        drink_sec_per_cow: dict[str, float] = defaultdict(float)
        active_feed_start: dict[str, float] = {}
        active_drink_start: dict[str, float] = {}

        def _close_feed(tag: str, t: float):
            if tag in active_feed_start:
                feed_sec_per_cow[tag] += t - active_feed_start.pop(tag)

        def _close_drink(tag: str, t: float):
            if tag in active_drink_start:
                drink_sec_per_cow[tag] += t - active_drink_start.pop(tag)

        for i, (img_path, cam_loc) in enumerate(zip(image_paths, camera_locations)):
            current_time = i * interval_sec
            img = imread_unicode(img_path)
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

            recognized_tag = None
            box_tags = []
            if cow_detected and boxes is not None:
                box_tags = id_recognizer.recognize_all_boxes(img, boxes)
                frame_tags.extend(box_tags)
                recognized_tag = format_tags(box_tags)
                state = zone_to_state(cam_loc)
            else:
                state = None

            present_tags = set(box_tags) if cow_detected else set()
            for tag in list(active_feed_start):
                if tag not in present_tags:
                    _close_feed(tag, current_time)
            for tag in list(active_drink_start):
                if tag not in present_tags:
                    _close_drink(tag, current_time)

            if cow_detected and state:
                for tag in box_tags:
                    if state == "питание":
                        if tag not in active_feed_start:
                            active_feed_start[tag] = current_time
                        _close_drink(tag, current_time)
                    elif state == "питье":
                        if tag not in active_drink_start:
                            active_drink_start[tag] = current_time
                        _close_feed(tag, current_time)

            _log(
                f"[{current_time:.0f} сек] "
                f"ID: {recognized_tag or '—'} | "
                f"Объектов: {cow_count} | "
                f"Уверенность: {avg_conf:.2f} | "
                f"Зона: {cam_loc} ({state_label(cam_loc)}) | "
                f"Состояние: {state or '—'}",
                progress_callback,
            )

            # Размеченный кадр
            annotated_path = None
            if show_frames or save_frames:
                annotated = _draw_annotated_frame(
                    img, boxes, state or "", cow_count, box_tags=box_tags
                )

                if show_frames:
                    cv2.imshow("Activity Analysis", annotated)
                    cv2.waitKey(1)

                if save_frames and annotated_dir:
                    fname          = f"frame_{i:03d}_t{int(current_time)}s_obj{cow_count}.jpg"
                    annotated_path = os.path.join(annotated_dir, fname)
                    imwrite_unicode(annotated_path, annotated)
                    _log(f"   💾 Кадр сохранён: {fname}", progress_callback)

            saved_img_path = annotated_path if annotated_path else img_path

            if cow_detected and boxes is not None:
                for idx, box in enumerate(boxes):
                    tag = box_tags[idx] if idx < len(box_tags) else str(idx + 1)
                    conf = float(box.conf[0])
                    cursor.execute(
                        """INSERT INTO frames
                               (session_id, timestamp_sec, cow_detected,
                                state, camera_location, image_path, confidence, recognized_tag)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (session_id, current_time, True,
                         state, cam_loc, saved_img_path, conf, tag),
                    )
            else:
                cursor.execute(
                    """INSERT INTO frames
                           (session_id, timestamp_sec, cow_detected,
                            state, camera_location, image_path, confidence, recognized_tag)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (session_id, current_time, False,
                     state, cam_loc, saved_img_path, avg_conf, None),
                )
            conn.commit()

        # Закрываем незакрытые интервалы
        last_time = (len(image_paths) - 1) * interval_sec
        for tag, start in list(active_feed_start.items()):
            feed_sec_per_cow[tag] += last_time - start + interval_sec
        for tag, start in list(active_drink_start.items()):
            drink_sec_per_cow[tag] += last_time - start + interval_sec

        cow_results = _build_cow_results(
            frame_tags, feed_sec_per_cow, drink_sec_per_cow, cow_number
        )
        total_feed_sec = sum(feed_sec_per_cow.values())
        total_drink_sec = sum(drink_sec_per_cow.values())

        session_tags = unique_tags(frame_tags)
        session_tag = ", ".join(session_tags) if session_tags else None
        primary_tag = dominant_tag(frame_tags)
        resolved_cow = resolve_cow_number(primary_tag, cow_number)
        cursor.execute(
            """UPDATE sessions
               SET total_duration_feed_sec  = %s,
                   total_duration_drink_sec = %s,
                   recognized_tag = %s,
                   cow_number = %s
               WHERE id = %s""",
            (total_feed_sec, total_drink_sec, session_tag, resolved_cow, session_id),
        )
        _save_cow_results(cursor, session_id, cow_results)
        conn.commit()

        if session_tag:
            _log(f"✅ Распознанные ID сессии: {session_tag}", progress_callback)
        for cr in cow_results:
            _log(
                f"✅ ID {cr['recognized_tag']}: "
                f"питание {cr['feed_sec']:.1f} сек, "
                f"питьё {cr['drink_sec']:.1f} сек",
                progress_callback,
            )
        _log(f"✅ Итого питание : {total_feed_sec:.1f} сек", progress_callback)
        _log(f"✅ Итого питьё   : {total_drink_sec:.1f} сек", progress_callback)
        if save_frames and annotated_dir:
            _log(f"📁 Размеченные кадры: {annotated_dir}", progress_callback)

        return total_feed_sec, total_drink_sec, session_tag, cow_results

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
        "кормовая зона", "кормовая зона", "питьевая зона",
        "питьевая зона", "кормовая зона", "кормовая зона",
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
