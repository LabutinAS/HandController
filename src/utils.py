# src/utils.py
import numpy as np
from pathlib import Path
import json

from database import get_user_calibration

# Файл JSON для обратной совместимости
BASE_DIR = Path(__file__).resolve().parent.parent
CALIB_FILE = BASE_DIR / 'models' / 'calibration.json'

# Загружаем JSON-scale, если есть
try:
    with open(CALIB_FILE, 'r') as f:
        data = json.load(f)
        CALIB_JSON_SCALE = float(data.get('scale', 0)) or None
except Exception:
    CALIB_JSON_SCALE = None

# Текущий пользователь для получения DB-scale
CURRENT_USER_ID = None


def set_current_user(user_id: int):
    """Устанавливает текущего пользователя для нормализации по БД"""
    global CURRENT_USER_ID
    CURRENT_USER_ID = user_id


def extract_landmark_vector(hand_landmarks) -> np.ndarray:
    """
    Преобразует MediaPipe hand_landmarks в вектор признаков shape (63,).
    """
    data = []
    for lm in hand_landmarks.landmark:
        data.extend([lm.x, lm.y, lm.z])
    return np.array(data, dtype=np.float32)


def normalize_vector(vect: np.ndarray) -> np.ndarray:
    """
    Центрирует по запястью (индекс 0) и масштабирует векторы:
    - Если есть DB-scale для CURRENT_USER_ID, используем его.
    - Иначе, если есть JSON-scale, используем его.
    - Иначе делим на локальный максимум.
    """
    v3 = vect.reshape(21, 3)
    # Центрирование по запястью
    v3_centered = v3 - v3[0:1, :]

    # Определение scale
    scale = None
    if CURRENT_USER_ID is not None:
        try:
            db_scale = get_user_calibration(CURRENT_USER_ID)
            if db_scale:
                scale = db_scale
        except Exception:
            scale = None
    if scale is None:
        scale = CALIB_JSON_SCALE or float(np.max(np.linalg.norm(v3_centered, axis=1))) or 1.0

    v3_scaled = v3_centered / scale
    return v3_scaled.reshape(-1)
