"""OpenCV capture + frame generator."""

from pathlib import Path

import cv2
import numpy as np


class VideoStream:
    def __init__(self, source: str = "demo/samples/test.mp4"):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise FileNotFoundError(
                f"[VigilAI] Cannot open video source: {source}"
            )

    def read_frame(self) -> tuple[bool, np.ndarray]:
        ret, frame = self.cap.read()
        return ret, frame

    def set_source(self, source: str):
        self.cap.release()
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise FileNotFoundError(
                f"[VigilAI] Cannot open video source: {source}"
            )
        self.source = source

    def release(self):
        self.cap.release()
