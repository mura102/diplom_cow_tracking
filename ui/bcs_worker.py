# ui/bcs_worker.py
from PyQt6.QtCore import QThread, pyqtSignal
import traceback


class BcsWorker(QThread):
    log_message = pyqtSignal(str)
    finished    = pyqtSignal(list)
    error       = pyqtSignal(str)

    def __init__(self, image_path: str, cow_id=None, stream_id=None, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.cow_id     = cow_id
        self.stream_id  = stream_id

    def run(self):
        try:
            from external_bcs.bcs_analysis import predict_bcs_all

            _, records = predict_bcs_all(
                image_path=self.image_path,
                cow_id=self.cow_id,
                stream_id=self.stream_id,
                save_result_image=True,
                result_image_path="bcs_result.jpg",
                logger=self.log_message.emit,
            )
            self.finished.emit(records)

        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")