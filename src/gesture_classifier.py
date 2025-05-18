import pickle
from pathlib import Path
import numpy as np

# Попробуем импорт из tensorflow или из чистого keras
try:
    from tensorflow.keras.models import load_model
except ImportError:
    from keras.models import load_model

# Определяем базовый каталог проекта (две папки вверх от этого файла)
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / 'models' / 'gesture_classifier.h5'
ENCODER_PATH = BASE_DIR / 'models' / 'label_encoder.pkl'

class GestureClassifier:
    """
    Обёртка над keras-моделью + sklearn LabelEncoder.
    Загружает модель и энкодер по абсолютным путям из папки models/.
    """
    def __init__(self):
        # Загружаем модель без компиляции (для инференса)
        self.model = load_model(str(MODEL_PATH), compile=False)
        # Загружаем энкодер меток
        with open(ENCODER_PATH, 'rb') as f:
            self.le = pickle.load(f)

    def predict(self, landmarks_batch: list[np.ndarray]) -> str:
        """
        Принимает список из WINDOW_SIZE векторов признаков shape (63,).
        Возвращает строковую метку жеста.
        """
        # Выполняем инференс без вывода прогресса
        probs = self.model.predict(np.stack(landmarks_batch), verbose=0)
        # Усредняем вероятности по окну и выбираем наибольшую
        avg = np.mean(probs, axis=0)
        idx = int(np.argmax(avg))
        return self.le.inverse_transform([idx])[0]
