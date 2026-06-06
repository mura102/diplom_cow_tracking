

import datetime
import os
import numpy as np
from collections import defaultdict
from pathlib import Path
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont

import cv2

from database.migrate_activity import migrate_activity_tables
from external_activity.cow_id import (
    dominant_tag,
    format_tags,
    get_id_recognizer,
    resolve_cow_number,
    unique_tags,
)
from external_activity.db_config import get_connection, get_default_cow_number
from vision.cv_io import imread_unicode, imwrite_unicode

# ── путь к модели относительно этого файла ────────────────────────────────────
_BASE_DIR  = Path(__file__).parent
MODEL_PATH = str(_BASE_DIR / "models" / "bestdown.pt")

IMAGE_PATHS = [
    'tests/down.jpg',
    'tests/down.jpg',
    'tests/up.jpg',
    'tests/up.jpg'
]
TIMESTAMPS = [
    datetime.datetime(2025, 1, 1, 22, 0, 0),
    datetime.datetime(2025, 1, 1, 22, 0, 30),
    datetime.datetime(2025, 1, 1, 22, 1, 0),
    datetime.datetime(2025, 1, 1, 22, 1, 30),
]
NIGHT_START = datetime.time(22, 0)
NIGHT_END   = datetime.time(5, 0)
FORCE_NIGHT = True

# модель загружается один раз при импорте модуля
model = YOLO(MODEL_PATH)


def put_text_pil(img, text, position, font_size=40, color=(0, 255, 0)):
    """Наложение текста с поддержкой кириллицы (тихая версия)"""
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)

    font = None
    possible_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except:
                continue
    if font is None:
        font = ImageFont.load_default()

    rgb_color = (color[2], color[1], color[0])
    draw.text((position[0], position[1] - font_size), text, font=font, fill=rgb_color)
    img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return img_bgr


def is_night_time(dt, night_start, night_end):
    current = dt.time()
    if night_start <= night_end:
        return night_start <= current <= night_end
    else:
        return current >= night_start or current <= night_end


def _build_sleep_cow_results(
    frame_tags: list[str],
    lying_sec: dict[str, float],
    standing_sec: dict[str, float],
    fallback_cow: int,
) -> list[dict]:
    tags = unique_tags(frame_tags + list(lying_sec.keys()) + list(standing_sec.keys()))
    results = []
    for tag in tags:
        cnum = resolve_cow_number(tag, fallback_cow)
        results.append({
            "recognized_tag": tag,
            "cow_number": cnum,
            "lying_sec": lying_sec.get(tag, 0.0),
            "standing_sec": standing_sec.get(tag, 0.0),
        })
    return results


def _save_sleep_cow_results(cursor, session_id: int, cow_results: list[dict]):
    for cr in cow_results:
        cursor.execute(
            """INSERT INTO sleep_cow_results
                   (session_id, recognized_tag, cow_number, lying_sec, standing_sec)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                session_id,
                cr["recognized_tag"],
                cr["cow_number"],
                cr["lying_sec"],
                cr["standing_sec"],
            ),
        )


def process_sleep_sequence(image_paths, timestamps, cow_number, night_start, night_end,
                           force_night, show_frames=False, save_frames=True,
                           output_dir='sleep_frames', interval_sec=2.0):
    if len(image_paths) != len(timestamps):
        raise ValueError("Количество изображений и временных меток не совпадает")

    if save_frames:
        run_time   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(output_dir, run_time)
        os.makedirs(output_dir, exist_ok=True)

    start_dt  = timestamps[0]
    rel_times = [(dt - start_dt).total_seconds() for dt in timestamps]
    if len(rel_times) > 1 and rel_times[-1] < interval_sec * 0.5:
        rel_times = [i * interval_sec for i in range(len(timestamps))]

    migrate_activity_tables()
    id_recognizer = get_id_recognizer()

    conn   = get_connection()
    cursor = conn.cursor()

    frame_tags: list[str] = []
    now_iso = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO sleep_sessions (cow_number, start_time, night_start, night_end, total_lying_sec,
        total_standing_sec, num_frames)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (cow_number, now_iso, night_start.strftime("%H:%M"), night_end.strftime("%H:%M"), 0.0, 0.0,
           len(image_paths)))
    session_id = cursor.fetchone()[0]
    conn.commit()

    total_lying           = 0.0
    total_standing        = 0.0
    lying_sec_per_cow: dict[str, float] = defaultdict(float)
    standing_sec_per_cow: dict[str, float] = defaultdict(float)
    active_lying_start    = {}
    active_standing_start = {}

    def _close_posture(tag, posture, rel_time, record):
        if posture == 'lying' and tag in active_lying_start:
            duration = rel_time - active_lying_start.pop(tag)
            if record:
                lying_sec_per_cow[tag] += duration
        elif posture == 'standing' and tag in active_standing_start:
            duration = rel_time - active_standing_start.pop(tag)
            if record:
                standing_sec_per_cow[tag] += duration

    for idx, (img_path, dt, rel_time) in enumerate(zip(image_paths, timestamps, rel_times)):
        img = imread_unicode(img_path)
        if img is None:
            print(f"[{dt.strftime('%H:%M:%S')}] Ошибка загрузки {img_path}")
            continue

        results      = model(img)
        boxes        = results[0].boxes
        detections   = []
        if boxes is not None and len(boxes) > 0:
            box_tags = id_recognizer.recognize_all_boxes(img, boxes)
            for bi, box in enumerate(boxes):
                cls = int(box.cls[0])
                posture = 'lying' if cls == 0 else 'standing'
                tag = box_tags[bi] if bi < len(box_tags) else str(bi + 1)
                detections.append({"tag": tag, "posture": posture, "box": box})
            frame_tags.extend(d["tag"] for d in detections)

        is_night         = is_night_time(dt, night_start, night_end)
        record_this_frame = (not force_night) or is_night

        present_tags = {d["tag"] for d in detections}
        for tag in list(active_lying_start):
            if tag not in present_tags:
                _close_posture(tag, 'lying', rel_time, record_this_frame)
        for tag in list(active_standing_start):
            if tag not in present_tags:
                _close_posture(tag, 'standing', rel_time, record_this_frame)

        for det in detections:
            tag = det["tag"]
            posture = det["posture"]
            if posture == 'lying':
                if tag not in active_lying_start:
                    active_lying_start[tag] = rel_time
                if tag in active_standing_start:
                    _close_posture(tag, 'standing', rel_time, record_this_frame)
            elif posture == 'standing':
                if tag not in active_standing_start:
                    active_standing_start[tag] = rel_time
                if tag in active_lying_start:
                    _close_posture(tag, 'lying', rel_time, record_this_frame)

        recognized_tag = format_tags([d["tag"] for d in detections]) if detections else None

        if record_this_frame:
            if detections:
                for det in detections:
                    cursor.execute('''
                        INSERT INTO sleep_frames
                            (session_id, timestamp_sec, datetime_iso, posture, image_path, recognized_tag)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (session_id, rel_time, dt.isoformat(), det["posture"], img_path, det["tag"]))
            else:
                cursor.execute('''
                    INSERT INTO sleep_frames
                        (session_id, timestamp_sec, datetime_iso, posture, image_path, recognized_tag)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (session_id, rel_time, dt.isoformat(), None, img_path, None))
            conn.commit()
            status = (
                f"ID:{recognized_tag} "
                f"{len(detections)} коров(ы) (ночь)" if detections else "no cow (ночь)"
            )
        else:
            status = (
                f"ID:{recognized_tag} "
                f"{len(detections)} коров(ы) (день, игнор)" if detections else "no cow (день, игнор)"
            )

        print(f"[{dt.strftime('%Y-%m-%d %H:%M:%S')}] {status}")

        if show_frames or save_frames:
            display_img = img.copy()
            if detections:
                for det in detections:
                    box = det["box"]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    pos = "лежит" if det["posture"] == 'lying' else "стоит"
                    label = f"ID:{det['tag']} {pos}"
                    display_img = put_text_pil(display_img, label, (x1, y1), font_size=48, color=(0, 255, 0))

            if show_frames:
                cv2.imshow("Sleep frame", display_img)
                cv2.waitKey(1)

            if save_frames:
                time_str     = dt.strftime("%Y%m%d_%H%M%S")
                out_filename = os.path.join(output_dir, f"sleep_frame_{idx:03d}_{time_str}.jpg")
                imwrite_unicode(out_filename, display_img)
                print(f"   Сохранён кадр: {out_filename}")

    last_rel_time = rel_times[-1] if rel_times else 0.0
    for tag, start in list(active_lying_start.items()):
        lying_sec_per_cow[tag] += last_rel_time - start + interval_sec
    for tag, start in list(active_standing_start.items()):
        standing_sec_per_cow[tag] += last_rel_time - start + interval_sec

    cow_results = _build_sleep_cow_results(
        frame_tags, lying_sec_per_cow, standing_sec_per_cow, cow_number
    )
    total_lying = sum(lying_sec_per_cow.values())
    total_standing = sum(standing_sec_per_cow.values())

    session_tags = unique_tags(frame_tags)
    session_tag = ", ".join(session_tags) if session_tags else None
    primary_tag = dominant_tag(frame_tags)
    resolved_cow = resolve_cow_number(primary_tag, cow_number)
    cursor.execute('''
        UPDATE sleep_sessions
        SET total_lying_sec    = %s,
            total_standing_sec = %s,
            recognized_tag     = %s,
            cow_number         = %s
        WHERE id = %s
    ''', (total_lying, total_standing, session_tag, resolved_cow, session_id))
    _save_sleep_cow_results(cursor, session_id, cow_results)
    conn.commit()

    print("\n=== ИТОГИ АНАЛИЗА СНА ===")
    if session_tag:
        print(f"Распознанные ID: {session_tag}")
    for cr in cow_results:
        print(
            f"ID {cr['recognized_tag']}: "
            f"лёжа {cr['lying_sec']:.1f} сек, "
            f"стоя {cr['standing_sec']:.1f} сек"
        )
    print(f"Итого лёжа: {total_lying:.1f} сек ({total_lying / 60:.2f} мин)")
    print(f"Итого стоя: {total_standing:.1f} сек ({total_standing / 60:.2f} мин)")

    cursor.close()
    conn.close()
    return total_lying, total_standing, session_tag, cow_results


if __name__ == "__main__":
    cow_number = get_default_cow_number()
    print(f"Анализ сна для коровы №{cow_number}")
    process_sleep_sequence(
        image_paths=IMAGE_PATHS,
        timestamps=TIMESTAMPS,
        cow_number=cow_number,
        night_start=NIGHT_START,
        night_end=NIGHT_END,
        force_night=FORCE_NIGHT,
        show_frames=False,
        save_frames=True,
        output_dir='sleep_frames'
    )
