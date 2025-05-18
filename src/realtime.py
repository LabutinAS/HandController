import cv2
import mediapipe as mp
import numpy as np
from collections import deque

from gesture_classifier import GestureClassifier
from utils import extract_landmark_vector, normalize_vector
from commands import execute as execute_command

# Размер скользящего окна
WINDOW_SIZE = 5


def main(device_id: int = 0):
    """
    Запуск распознавания жестов с выбранного видео-устройства.

    Args:
        device_id: индекс камеры для захвата (0, 1, ...)
    """
    # Инициализация камеры
    cap = cv2.VideoCapture(device_id)
    if not cap.isOpened():
        print(f"Не удалось открыть видеоустройство #{device_id}")
        return

    classifier = GestureClassifier()
    prediction_window = deque(maxlen=WINDOW_SIZE)
    last_label = None

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    print(f"=== Запуск распознавания на устройстве #{device_id} ===")
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as hands:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Отзеркалить для удобства и преобразовать
            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(frame_rgb)

            # Обработка левой руки
            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness
                ):
                    if handedness.classification[0].label == 'Left':
                        # Рисуем скелет
                        mp_drawing.draw_landmarks(
                            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                        # Извлечение и нормализация признаков
                        raw_vect = extract_landmark_vector(hand_landmarks)
                        norm_vect = normalize_vector(raw_vect)
                        prediction_window.append(norm_vect)

                        # Классификация при полном окне
                        if len(prediction_window) == WINDOW_SIZE:
                            pred = classifier.predict(list(prediction_window))
                            prediction_window.clear()
                            if pred != last_label:
                                last_label = pred
                                execute_command(pred)
                        break

            # Вывод метки на экран
            if last_label is not None:
                cv2.putText(
                    frame,
                    f'Gesture: {last_label}',
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

            cv2.imshow('Hand Gesture Recognition', frame)
            if cv2.waitKey(1) & 0xFF in (27, ord('q')):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    # По умолчанию используем устройство 0
    main()
