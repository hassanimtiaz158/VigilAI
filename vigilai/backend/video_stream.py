"""OpenCV capture + frame generator."""

import cv2
import numpy as np


class VideoStream:
    def __init__(self, source: str = "demo/samples/construction.mp4"):
        self.cap = cv2.VideoCapture(source)
        self.source = source

    def read_frame(self) -> tuple[bool, np.ndarray]:
        # TODO: implement frame reading with loop-on-end
        ret, frame = self.cap.read()
        return ret, frame

    def set_source(self, source: str):
        # TODO: implement source switching
        self.source = source

    def release(self):
        self.cap.release()
