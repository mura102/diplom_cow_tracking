import os
import platform
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

TARGET_FPS        = 30
FRAME_INTERVAL    = 1.0 / TARGET_FPS
SNAPSHOT_INTERVAL = 2.0

BASE_DIR        = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR   = BASE_DIR / "snapshots"
FEED_FRAMES_DIR = BASE_DIR / "feed_frames"

if platform.system() == "Windows":
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"


class VideoWorker(QThread):
    """
    Поток захвата видеопотока с веб-камеры или видеофайла.

    Возможности:
    - безопасное чтение кадров через OpenCV,
    - показ кадров в UI,
    - автосохранение снимков каждые 2 секунды,
    - передача списка снимков в AnalysisWorker после завершения видео.
    """
    change_pixmap_signal = pyqtSignal(QImage)
    frame_ready_signal   = pyqtSignal(object)
    snapshots_ready      = pyqtSignal(list, list)
    log_signal           = pyqtSignal(str)

    def __init__(self, camera_index=0, source=None):
        super().__init__()
        self.source          = source if source is not None else camera_index
        self.is_running      = False
        self.cap             = None
        self._cleaned_up     = False
        self._is_file_source = isinstance(self.source, str)
        self._saved_paths    = []
        self._saved_timestamps = []

    def run(self):
        self.is_running    = True
        self._cleaned_up   = False
        self._saved_paths  = []
        self._saved_timestamps = []
        dropped_frames     = 0

        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        self.log_signal.emit(
            f"Инициализация видеопотока для источника: {self.source}..."
        )
        self.cap = self._open_capture(self.source)

        if self.cap is None or not self.cap.isOpened():
            self.log_signal.emit(
                f"ОШИБКА: Не удалось подключиться к источнику {self.source}."
            )
            self.is_running = False
            return

        self.log_signal.emit("Канал захвата успешно открыт. Начало трансляции.")

        fps = self.cap.get(cv2.CAP_PROP_FPS) if self._is_file_source else 0
        if not fps or fps <= 1 or fps > 240:
            fps = TARGET_FPS
        frames_per_snapshot = max(1, int(round(fps * SNAPSHOT_INTERVAL)))

        frame_index              = 0
        last_snapshot_monotonic  = time.monotonic()

        while self.is_running:
            frame_start = time.monotonic()

            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    dropped_frames += 1
                    if dropped_frames >= 3:
                        self.log_signal.emit(
                            "Трансляция завершена или устойчивая потеря сигнала."
                        )
                        break
                    time.sleep(0.02)
                    continue

                dropped_frames = 0
                frame_index   += 1

                self.frame_ready_signal.emit(frame.copy())

                if self._is_file_source:
                    should_snapshot = (frame_index % frames_per_snapshot == 0)
                else:
                    now = time.monotonic()
                    should_snapshot = (now - last_snapshot_monotonic) >= SNAPSHOT_INTERVAL

                if should_snapshot:
                    ts       = datetime.now()
                    filename = f"snapshot_{ts.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                    filepath = SNAPSHOTS_DIR / filename
                    ok = cv2.imwrite(str(filepath), frame)
                    if ok:
                        self._saved_paths.append(str(filepath))
                        self._saved_timestamps.append(ts)
                        self.log_signal.emit(f"📸 Снимок сохранён: {filename}")
                    else:
                        self.log_signal.emit(
                            f"⚠️ Не удалось сохранить снимок: {filename}"
                        )
                    last_snapshot_monotonic = time.monotonic()

                rgb_image      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch       = rgb_image.shape
                bytes_per_line = ch * w
                qt_img = QImage(
                    rgb_image.data, w, h,
                    bytes_per_line,
                    QImage.Format.Format_RGB888,
                ).copy()

                if self.is_running:
                    self.change_pixmap_signal.emit(qt_img)

            except Exception as e:
                self.log_signal.emit(f"Сбой кадра: {e}")
                break

            elapsed    = time.monotonic() - frame_start
            sleep_time = FRAME_INTERVAL - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        if self._saved_paths:
            self.log_signal.emit(
                f"Подготовлено снимков для анализа: {len(self._saved_paths)}"
            )
            self.snapshots_ready.emit(self._saved_paths, self._saved_timestamps)
        else:
            self.log_signal.emit("⚠️ Снимки не были подготовлены для анализа.")

        self.cleanup()

    def _open_capture(self, source) -> cv2.VideoCapture:
        if isinstance(source, int):
            if platform.system() == "Windows":
                self.log_signal.emit("ОС Windows: открываем камеру через MSMF...")
                return cv2.VideoCapture(source, cv2.CAP_MSMF)
            return cv2.VideoCapture(source)

        if platform.system() == "Windows":
            self.log_signal.emit("ОС Windows: открываем файл через FFMPEG...")
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            if cap is not None and cap.isOpened():
                return cap
            self.log_signal.emit(
                "FFMPEG недоступен, пробуем открыть файл стандартным способом..."
            )
        return cv2.VideoCapture(source)

    def stop(self):
        self.is_running = False

    def cleanup(self):
        if self._cleaned_up:
            return
        self._cleaned_up = True
        try:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            self.log_signal.emit("Ресурсы видеопотока успешно освобождены.")
        except Exception as e:
            print(f"Ошибка при закрытии камеры: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Глобальный Lock для безопасной инициализации YOLO-детектора.
# Гарантирует что модель загружается ровно один раз,
# даже если в будущем запустятся два AnalysisWorker одновременно.
# На текущую однопоточную работу не влияет — Lock захватывается мгновенно.
# ─────────────────────────────────────────────────────────────────────────────
_detector_lock = threading.Lock()


class AnalysisWorker(QThread):
    """
    Поток анализа серии снимков через external_activity.activity_analysis.

    На вход получает:
    - image_paths
    - timestamps
    - camera_location
    - cow_number

    На выходе возвращает dict в формате, который ожидает main_window.py.
    """
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(
        self,
        image_paths: list,
        timestamps: list,
        camera_location: str = "кормушка",
        cow_number: int = 1,
        parent=None,
    ):
        super().__init__(parent)
        self.image_paths     = image_paths
        self.timestamps      = timestamps
        self.camera_location = camera_location
        self.cow_number      = cow_number

    def run(self):
        try:
            if not self.image_paths:
                raise ValueError("Список снимков пуст. Анализировать нечего.")

            self.progress.emit(
                f"Начало анализа активности: {len(self.image_paths)} кадров..."
            )
            result = self._analyze_activity()
            self.progress.emit("Анализ завершён.")
            self.finished.emit(result)
        except Exception as e:
            import traceback
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def _analyze_activity(self) -> dict:
        # Lock гарантирует безопасную инициализацию _detector внутри
        # activity_analysis._get_detector() при параллельных запусках
        with _detector_lock:
            from external_activity.activity_analysis import process_sequence

        self.progress.emit("Загрузка модели и запуск анализа снимков...")
        FEED_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
        camera_locations = [self.camera_location] * len(self.image_paths)

        feed_sec_total, drink_sec_total = process_sequence(
            image_paths=self.image_paths,
            camera_locations=camera_locations,
            cow_number=self.cow_number,
            interval_sec=SNAPSHOT_INTERVAL,
            show_frames=False,
            save_frames=True,
            output_dir=str(FEED_FRAMES_DIR),
            progress_callback=self.progress.emit,
        )

        feed_sec_total  = int(round(feed_sec_total))
        drink_sec_total = int(round(drink_sec_total))

        self.progress.emit(
            f"Результат получен: кормление {feed_sec_total} сек, "
            f"питьё {drink_sec_total} сек."
        )

        return {
            "cow_number": self.cow_number,
            "camera":     self.camera_location,
            "num_frames": len(self.image_paths),
            "feed_min":   feed_sec_total  // 60,
            "feed_sec":   feed_sec_total  %  60,
            "drink_min":  drink_sec_total // 60,
            "drink_sec":  drink_sec_total %  60,
        }
