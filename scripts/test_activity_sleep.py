"""Тест активности и сна с распознаванием ID на видео."""
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

env_path = ROOT / ".env"
if env_path.is_file():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

VIDEO = r"D:\ВКР\PythonProject\bcs\tests\PixVerse_V6_Image_Text_360P_ozhivi_foto_lezhacha_1.mp4"
SNAPSHOT_INTERVAL = 2.0


def extract_snapshots(video_path: str):
    import cv2

    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    frames_per = max(1, int(round(fps * SNAPSHOT_INTERVAL)))
    out_dir = ROOT / "snapshots" / "test_run"
    out_dir.mkdir(parents=True, exist_ok=True)

    paths, timestamps = [], []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        idx += 1
        if idx % frames_per != 0:
            continue
        ts = datetime.now()
        from vision.cv_io import imwrite_unicode

        p = out_dir / f"snap_{len(paths):03d}.jpg"
        imwrite_unicode(str(p), frame)
        paths.append(str(p))
        timestamps.append(ts)
    cap.release()
    print(f"Snapshots: {len(paths)}")
    return paths, timestamps


def _print_db_ids():
    from external_activity.db_config import get_connection

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, cow_number, recognized_tag, total_duration_feed_sec "
        "FROM sessions ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    print("DB sessions:", row)

    if row:
        cur.execute(
            "SELECT timestamp_sec, recognized_tag, state FROM frames "
            "WHERE session_id = %s ORDER BY timestamp_sec, recognized_tag",
            (row[0],),
        )
        print("DB frames:", cur.fetchall())

        cur.execute(
            "SELECT recognized_tag, cow_number, feed_sec, drink_sec "
            "FROM activity_cow_results WHERE session_id = %s ORDER BY recognized_tag",
            (row[0],),
        )
        print("DB activity_cow_results:", cur.fetchall())

    cur.execute(
        "SELECT id, cow_number, recognized_tag, total_lying_sec "
        "FROM sleep_sessions ORDER BY id DESC LIMIT 1"
    )
    srow = cur.fetchone()
    print("DB sleep_sessions:", srow)

    if srow:
        cur.execute(
            "SELECT timestamp_sec, recognized_tag, posture FROM sleep_frames "
            "WHERE session_id = %s ORDER BY timestamp_sec, recognized_tag",
            (srow[0],),
        )
        print("DB sleep_frames:", cur.fetchall())

        cur.execute(
            "SELECT recognized_tag, cow_number, lying_sec, standing_sec "
            "FROM sleep_cow_results WHERE session_id = %s ORDER BY recognized_tag",
            (srow[0],),
        )
        print("DB sleep_cow_results:", cur.fetchall())

    conn.close()


def main():
    from database.migrate_activity import migrate_activity_tables

    migrate_activity_tables()

    paths, timestamps = extract_snapshots(VIDEO)
    if not paths:
        print("ERROR: no snapshots")
        return 1

    print("\n--- ACTIVITY + ID (видео-тест: Кормовая зона) ---")
    try:
        from external_activity.activity_analysis import process_sequence
        from external_activity.db_config import get_default_cow_number

        feed, drink, tag, cow_results = process_sequence(
            paths,
            [],
            get_default_cow_number(),
            interval_sec=SNAPSHOT_INTERVAL,
            save_frames=False,
            progress_callback=print,
            activity_zone="Кормовая зона",
        )
        print(f"OK feed zone: ID={tag}, feed={feed:.1f}s, drink={drink:.1f}s")
        for cr in cow_results:
            print(f"  cow {cr['recognized_tag']}: feed={cr['feed_sec']:.1f}s")
        assert feed > 0 and drink == 0, "Кормовая зона должна давать питание"

        feed2, drink2, tag2, cow_results2 = process_sequence(
            paths,
            [],
            get_default_cow_number(),
            interval_sec=SNAPSHOT_INTERVAL,
            save_frames=False,
            progress_callback=print,
            activity_zone="Питьевая зона",
        )
        print(f"OK drink zone: ID={tag2}, feed={feed2:.1f}s, drink={drink2:.1f}s")
        assert drink2 > 0 and feed2 == 0, "Питьевая зона должна давать питьё"
    except Exception as e:
        print(f"FAIL activity: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n--- SLEEP + ID ---")
    try:
        import datetime as dt
        from external_activity.sleep_analysis import process_sleep_sequence
        from external_activity.db_config import get_default_cow_number

        lying, standing, tag, sleep_cows = process_sleep_sequence(
            paths,
            timestamps,
            get_default_cow_number(),
            night_start=dt.time(22, 0),
            night_end=dt.time(5, 0),
            force_night=False,
            save_frames=False,
            interval_sec=SNAPSHOT_INTERVAL,
        )
        print(f"OK sleep: ID={tag}, lying={lying:.1f}s, standing={standing:.1f}s")
        for cr in sleep_cows:
            print(f"  cow {cr['recognized_tag']}: lying={cr['lying_sec']:.1f}s")
    except Exception as e:
        print(f"FAIL sleep: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n--- DB CHECK ---")
    _print_db_ids()
    return 0


if __name__ == "__main__":
    sys.exit(main())
