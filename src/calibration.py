import os
# Отключение логов
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
try:
    from absl import logging as absl_logging
    absl_logging.set_verbosity(absl_logging.ERROR)
except ImportError:
    pass

import cv2
import mediapipe as mp
import numpy as np
import time
from pathlib import Path
from collections import deque

from gesture_classifier import GestureClassifier
from utils import extract_landmark_vector, normalize_vector
from database import set_user_calibration

# Жесты для калибровки и время удержания (сек)
CALIB_GESTURES = ['A', 'M', 'S', 'W']
HOLD_TIME = 2.0
WINDOW_SIZE = 5  # Размер скользящего окна для распознавания

# Пути (для совместимости)
BASE_DIR = Path(__file__).resolve().parent.parent
CALIB_FILE = BASE_DIR / 'models' / 'calibration.json'


def main(user_id: int, device_id: int = 0):
    """
    Калибровка: ждём первого детекта моделью,
    затем удерживаем HOLD_TIME секунд, собираем max_dist и
    сохраняем scale в БД для данного user_id.

    Args:
        user_id: ID текущего пользователя
        device_id: индекс видеоустройства для захвата
    """
    cap = cv2.VideoCapture(device_id)
    if not cap.isOpened():
        print(f"Не удалось открыть видеоустройство #{device_id}")
        return

    mp_hands = mp.solutions.hands
    classifier = GestureClassifier()
    prediction_window = deque(maxlen=WINDOW_SIZE)

    print("=== Начинаем калибровку ===")
    print(f"Используется устройство #{device_id}. Будут калиброваны жесты: {', '.join(CALIB_GESTURES)}")

    dist_map = {g: [] for g in CALIB_GESTURES}

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as hands:
        for gesture in CALIB_GESTURES:
            print(f"Покажите жест '{gesture}' для распознавания...")
            detected = False
            while not detected:
                ret, frame = cap.read()
                if not ret:
                    continue
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)
                if results.multi_hand_landmarks and results.multi_handedness:
                    for lm, handed in zip(results.multi_hand_landmarks, results.multi_handedness):
                        if handed.classification[0].label == 'Left':
                            raw_vect = extract_landmark_vector(lm)
                            norm_vect = normalize_vector(raw_vect)
                            prediction_window.append(norm_vect)
                            if len(prediction_window) == WINDOW_SIZE:
                                pred = classifier.predict(list(prediction_window))
                                if pred == gesture:
                                    detected = True
                                    print(f"Жест '{gesture}' распознан. Начало удержания {HOLD_TIME} сек...")
                                    prediction_window.clear()
                                else:
                                    prediction_window.popleft()
                            break
                cv2.putText(frame, f"Detect: {gesture}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                cv2.imshow('Calibration', frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    print("Калибровка прервана пользователем.")
                    cap.release()
                    cv2.destroyAllWindows()
                    return

            start_time = time.time()
            while time.time() - start_time < HOLD_TIME:
                ret2, frame2 = cap.read()
                if not ret2:
                    continue
                frame2 = cv2.flip(frame2, 1)
                rgb2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
                res2 = hands.process(rgb2)
                if res2.multi_hand_landmarks and res2.multi_handedness:
                    for lm2, hd in zip(res2.multi_hand_landmarks, res2.multi_handedness):
                        if hd.classification[0].label == 'Left':
                            vect2 = extract_landmark_vector(lm2)
                            v3 = vect2.reshape(21, 3)
                            centered = v3 - v3[0:1, :]
                            max_d = float(np.max(np.linalg.norm(centered, axis=1)))
                            dist_map[gesture].append(max_d)
                            mp.solutions.drawing_utils.draw_landmarks(
                                frame2, lm2, mp_hands.HAND_CONNECTIONS)
                            break
                cv2.putText(frame2, f"Hold: {gesture}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 2)
                cv2.imshow('Calibration', frame2)
                if cv2.waitKey(1) & 0xFF == 27:
                    print("Калибровка прервана пользователем.")
                    cap.release()
                    cv2.destroyAllWindows()
                    return
            time.sleep(0.5)

    cap.release()
    cv2.destroyAllWindows()

    means = [np.mean(vals) for vals in dist_map.values() if vals]
    if not means:
        print("Калибровка не удалась: нет данных.")
        return
    calib_scale = float(np.mean(means))
    set_user_calibration(user_id, calib_scale)
    print(f"Калибровка завершена. Scale={calib_scale:.4f} сохранён для user_id={user_id}.")
