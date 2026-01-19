import cv2
import numpy as np
import face_recognition


def extract_embedding(image_bytes: bytes) -> list[float]:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Invalid JPEG")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    faces = face_recognition.face_locations(rgb)
    if not faces:
        raise ValueError("No face found")
    return face_recognition.face_encodings(rgb, faces)[0].tolist()
