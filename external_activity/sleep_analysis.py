

import cv2
import datetime
import os
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont

# ── импорт подключения к БД ───────────────────────────────────────────────────
from external_activity.db_config import get_connection, get_default_cow_number

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


def process_sleep_sequence(image_paths, timestamps, cow_number, night_start, night_end,
                           force_night, show_frames=False, save_frames=True,
                           output_dir='sleep_frames'):
    if len(image_paths) != len(timestamps):
        raise ValueError("Количество изображений и временных меток не совпадает")

    if save_frames:
        run_time   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(output_dir, run_time)
        os.makedirs(output_dir, exist_ok=True)

    start_dt  = timestamps[0]
    rel_times = [(dt - start_dt).total_seconds() for dt in timestamps]

    conn   = get_connection()
    cursor = conn.cursor()

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
    active_lying_start    = None
    active_standing_start = None

    for idx, (img_path, dt, rel_time) in enumerate(zip(image_paths, timestamps, rel_times)):
        img = cv2.imread(img_path)
        if img is None:
            print(f"[{dt.strftime('%H:%M:%S')}] Ошибка загрузки {img_path}")
            continue

        results      = model(img)
        cow_detected = False
        posture      = None
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            cow_detected = True
            cls     = int(results[0].boxes.cls[0])
            posture = 'lying' if cls == 0 else 'standing'

        is_night         = is_night_time(dt, night_start, night_end)
        record_this_frame = (not force_night) or is_night

        if cow_detected:
            if posture == 'lying':
                if active_lying_start is None:
                    active_lying_start = rel_time
                if active_standing_start is not None:
                    duration = rel_time - active_standing_start
                    if record_this_frame:
                        total_standing += duration
                    active_standing_start = None
            elif posture == 'standing':
                if active_standing_start is None:
                    active_standing_start = rel_time
                if active_lying_start is not None:
                    duration = rel_time - active_lying_start
                    if record_this_frame:
                        total_lying += duration
                    active_lying_start = None
        else:
            if active_lying_start is not None:
                duration = rel_time - active_lying_start
                if record_this_frame:
                    total_lying += duration
                active_lying_start = None
            if active_standing_start is not None:
                duration = rel_time - active_standing_start
                if record_this_frame:
                    total_standing += duration
                active_standing_start = None

        if record_this_frame:
            cursor.execute('''
                INSERT INTO sleep_frames (session_id, timestamp_sec, datetime_iso, posture, image_path)
                VALUES (%s, %s, %s, %s, %s)
            ''', (session_id, rel_time, dt.isoformat(), posture, img_path))
            conn.commit()
            status = f"{posture if posture else 'no cow'} (ночь)"
        else:
            status = f"{posture if posture else 'no cow'} (день, игнор)"

        print(f"[{dt.strftime('%Y-%m-%d %H:%M:%S')}] {status}")

        if show_frames or save_frames:
            display_img = img.copy()
            if cow_detected and results[0].boxes is not None:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    label = "лежит" if posture == 'lying' else ("стоит" if posture == 'standing' else "корова")
                    display_img = put_text_pil(display_img, label, (x1, y1), font_size=48, color=(0, 255, 0))

            if show_frames:
                cv2.imshow("Sleep frame", display_img)
                cv2.waitKey(1)

            if save_frames:
                time_str     = dt.strftime("%Y%m%d_%H%M%S")
                out_filename = os.path.join(output_dir, f"sleep_frame_{idx:03d}_{time_str}.jpg")
                cv2.imwrite(out_filename, display_img)
                print(f"   Сохранён кадр: {out_filename}")

    last_rel_time = rel_times[-1]
    if active_lying_start is not None:
        duration = last_rel_time - active_lying_start
        total_lying += duration
    if active_standing_start is not None:
        duration = last_rel_time - active_standing_start
        total_standing += duration

    cursor.execute('''
        UPDATE sleep_sessions
        SET total_lying_sec    = %s,
            total_standing_sec = %s
        WHERE id = %s
    ''', (total_lying, total_standing, session_id))
    conn.commit()

    print("\n=== ИТОГИ АНАЛИЗА СНА ===")
    print(f"Время лёжа: {total_lying:.1f} сек ({total_lying / 60:.2f} мин)")
    print(f"Время стоя (нарушение сна): {total_standing:.1f} сек ({total_standing / 60:.2f} мин)")

    cursor.close()
    conn.close()
    return total_lying, total_standing


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
