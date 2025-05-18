# src/commands.py
import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Callable, Dict

from database import get_user_scripts

# Каталог со скриптами (bash и bat) относительно корня проекта
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / 'scripts'
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# Хранит пользовательские привязки: жест -> имя скрипта
USER_SCRIPTS: Dict[str, str] = {}


def load_user_scripts(user_id: int) -> None:
    """
    Загружает из БД скрипты для данного пользователя
    и обновляет USER_SCRIPTS.
    """
    USER_SCRIPTS.clear()
    scripts = get_user_scripts(user_id)
    for gesture, script in scripts.items():
        USER_SCRIPTS[gesture] = script


def run_bash_script(script_name: str) -> None:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"[commands] Скрипт не найден: {script_path}")
        return
    try:
        subprocess.Popen(['bash', str(script_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[commands] Ошибка при запуске bash-скрипта {script_name}: {e}")


def run_bat_script(script_name: str) -> None:
    bat_path = SCRIPTS_DIR / script_name
    if not bat_path.exists():
        print(f"[commands] BAT-скрипт не найден: {bat_path}")
        return
    try:
        subprocess.Popen(['cmd.exe', '/C', str(bat_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[commands] Ошибка при запуске BAT-скрипта {script_name}: {e}")


def say_hello_world() -> None:
    """Команда для жеста SCH"""
    print("Hello WORLD")


def exit_letter() -> None:
    """Команда для жеста Q: закрывает окна и завершает приложение"""
    import cv2
    cv2.destroyAllWindows()
    sys.exit(0)


def open_my_computer() -> None:
    """Открывает "Этот компьютер" через соответствующий скрипт"""
    if platform.system() == 'Windows':
        run_bat_script('open_computer.bat')
    else:
        run_bash_script('open_computer.sh')


def do_nothing() -> None:
    """Заглушка для жестов без команды"""
    pass

# Статические команды, если пользователь их не переопределил
STATIC_COMMANDS: Dict[str, Callable[[], None]] = {
    'SCH': say_hello_world,
    'Q': exit_letter,
    'X': open_my_computer,
    'A' : do_nothing
}


def execute(gesture_label: str) -> None:
    """
    Выполняет команду для распознанного жеста:
    - Сначала пробует пользовательский скрипт из USER_SCRIPTS
    - Если нет, использует STATIC_COMMANDS
    """
    # Пользовательские скрипты
    script = USER_SCRIPTS.get(gesture_label)
    if script:
        # Определяем по расширению
        if script.lower().endswith('.bat'):
            run_bat_script(script)
        else:
            run_bash_script(script)
        return

    # Статические команды
    func = STATIC_COMMANDS.get(gesture_label, do_nothing)
    func()
