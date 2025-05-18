import time
import sys
import re
import os
import shutil
from pathlib import Path
import customtkinter as ctk
import cv2
from tkinter import filedialog

# Добавляем папку src в sys.path для импорта
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from database import init_db, create_user, authenticate_user, set_user_script
from commands import load_user_scripts, STATIC_COMMANDS, SCRIPTS_DIR
from utils import set_current_user
import realtime
import calibration

# Инициализация базы данных при старте приложения
init_db()

# Константы стиля
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 50
BUTTON_CORNER_RADIUS = 12

# Регулярки для валидации
ALNUM_PATTERN = re.compile(r'^[A-Za-z0-9]+$')
NAME_PATTERN  = re.compile(r'^[A-Za-zА-Яа-яЁё ]+$')

# Доступные жесты для назначения скриптов
GESTURE_OPTIONS = list(STATIC_COMMANDS.keys())

# Поиск камер
from commands import SCRIPTS_DIR  # ensure scripts dir exists
def find_cameras(max_tested=5):
    cams = []
    for i in range(max_tested):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cams.append((i, f"Camera {i}"))
            cap.release()
    return cams

class GestureApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Hand Gesture App')
        self.geometry('450x480')
        self.resizable(False, False)
        self.current_user_id = None
        self.selected_device = 0

        # Фреймы
        self.login_frame = ctk.CTkFrame(master=self)
        self.main_frame = ctk.CTkFrame(master=self)
        self.login_frame.pack(expand=True, fill='both')
        self._build_login()
        self._build_main_menu()

    def _build_login(self):
        ctk.CTkLabel(self.login_frame, text="Username:").pack(pady=(20,5))
        self.username_entry = ctk.CTkEntry(self.login_frame)
        self.username_entry.pack(pady=5)
        ctk.CTkLabel(self.login_frame, text="Password:").pack(pady=(10,5))
        self.password_entry = ctk.CTkEntry(self.login_frame, show="*")
        self.password_entry.pack(pady=5)
        btn_frame = ctk.CTkFrame(self.login_frame)
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Войти", width=100, command=self._on_login).pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text="Регистрация", width=100, command=self._open_register_window).pack(side='right', padx=10)
        self.msg_label = ctk.CTkLabel(self.login_frame, text="", text_color="#ff0000")
        self.msg_label.pack(pady=(5,0))

    def _build_main_menu(self):
        # Камеры
        cams = find_cameras()
        ctk.CTkLabel(self.main_frame, text="Выберите камеру:").pack(pady=(20,5))
        self.cam_map = {f"Camera {i}": i for i,_ in cams}
        self.cam_selector = ctk.CTkComboBox(self.main_frame, values=list(self.cam_map.keys()), command=self._on_camera_select)
        default = list(self.cam_map.keys())[0] if self.cam_map else 'Camera 0'
        self.cam_selector.set(default)
        self.selected_device = self.cam_map.get(default, 0)
        self.cam_selector.pack(pady=5)
        # Кнопки
        self.calib_btn = ctk.CTkButton(self.main_frame, text='КАЛИБРОВКА', width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
            corner_radius=BUTTON_CORNER_RADIUS, fg_color="#ffc107", hover_color="#e0a800", command=self.on_calibrate)
        self.calib_btn.pack(pady=(30,10))
        self.start_btn = ctk.CTkButton(self.main_frame, text='ЗАПУСК', width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
            corner_radius=BUTTON_CORNER_RADIUS, fg_color="#1f6aa5", hover_color="#155175", command=self.on_start)
        self.start_btn.pack(pady=(0,10))
        self.add_script_btn = ctk.CTkButton(self.main_frame, text='Добавить скрипт', width=BUTTON_WIDTH,
            height=BUTTON_HEIGHT, corner_radius=BUTTON_CORNER_RADIUS, fg_color="#5bc0de", hover_color="#31b0d5",
            command=self._open_add_script_dialog)
        self.add_script_btn.pack(pady=(0,10))
        ctk.CTkButton(self.main_frame, text='ВЫЙТИ', width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
            corner_radius=BUTTON_CORNER_RADIUS, fg_color="#d9534f", hover_color="#b52b27", command=self._on_logout).pack()

    def _validate_credentials(self, u,p): return bool(u and p and ALNUM_PATTERN.fullmatch(u) and ALNUM_PATTERN.fullmatch(p))

    def _on_login(self):
        u, p = self.username_entry.get().strip(), self.password_entry.get().strip()
        if not self._validate_credentials(u,p): self.msg_label.configure(text="Логин/пароль: буквы или цифры"); return
        uid = authenticate_user(u,p)
        if uid:
            self.current_user_id = uid
            load_user_scripts(uid)
            self.msg_label.configure(text="")
            self._show_main_menu()
        else:
            self.msg_label.configure(text="Неверный логин или пароль")

    def _open_register_window(self):
        # Окно регистрации нового пользователя
        reg = ctk.CTkToplevel(self)
        reg.title("Регистрация")
        reg.geometry('450x350')
        reg.resizable(False, False)

        # Поле Username
        ctk.CTkLabel(reg, text="Username:").pack(pady=(20,5))
        user_ent = ctk.CTkEntry(reg)
        user_ent.pack(pady=5)

        # Поле Password
        ctk.CTkLabel(reg, text="Password:").pack(pady=(10,5))
        pwd_ent = ctk.CTkEntry(reg, show="*")
        pwd_ent.pack(pady=5)

        # Поле ФИО
        ctk.CTkLabel(reg, text="ФИО:").pack(pady=(10,5))
        fio_ent = ctk.CTkEntry(reg)
        fio_ent.pack(pady=5)

        # Сообщение об ошибках
        msg = ctk.CTkLabel(reg, text="", text_color="#ff0000")
        msg.pack(pady=(5,0))

        # Обработчик кнопки регистрации
        def on_register():
            u = user_ent.get().strip()
            p = pwd_ent.get().strip()
            f = fio_ent.get().strip()
            # Валидация: username/password алфавитно-цифровые, ФИО буквы и пробелы
            if not (ALNUM_PATTERN.fullmatch(u) and ALNUM_PATTERN.fullmatch(p) and f and NAME_PATTERN.fullmatch(f)):
                msg.configure(text="Проверьте поля: только буквы и цифры для логина/пароля, ФИО без цифр/символов")
                return
            # Создание пользователя
            if create_user(u, p, f):
                msg.configure(text="Пользователь создан", text_color="#00aa00")
                time.sleep(0.5)
                reg.destroy()
            else:
                msg.configure(text="Имя занято или неверно")

        # Кнопки OK и Отмена
        btn_frame = ctk.CTkFrame(reg)
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="OK", width=80, command=on_register).pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text="Отмена", width=80, command=reg.destroy).pack(side='right', padx=10)

    def _on_camera_select(self, name):
        """Обработка выбора камеры из выпадающего списка"""
        self.selected_device = self.cam_map.get(name, 0)

    def _show_main_menu(self): self.login_frame.pack_forget(); self.main_frame.pack(expand=True,fill='both')

    def on_calibrate(self):
        set_current_user(self.current_user_id)
        self.calib_btn.configure(text='Калибруем...',state='disabled'); self.update(); time.sleep(0.5)
        calibration.main(self.current_user_id, self.selected_device)
        self.calib_btn.configure(text='КАЛИБРОВКА',state='normal')

    def on_start(self):
        set_current_user(self.current_user_id)
        self.start_btn.configure(text='Загрузка...',state='disabled'); self.update(); time.sleep(1)
        self.run_recognition=True; self.destroy()

    def _open_add_script_dialog(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Добавить скрипт"); dlg.geometry('450x350'); dlg.resizable(False,False)
        ctk.CTkLabel(dlg,text="Жест:").pack(pady=(15,5)); self.gesture_cb = ctk.CTkComboBox(dlg, values=GESTURE_OPTIONS); self.gesture_cb.pack(pady=5)
        ctk.CTkLabel(dlg,text="Файл (.bat/.sh):").pack(pady=(10,5))
        entry = ctk.CTkEntry(dlg, width=200); entry.pack(pady=5)
        def browse():
            path = filedialog.askopenfilename(filetypes=[("Scripts","*.bat *.sh")])
            if path: entry.delete(0,'end'); entry.insert(0,path)
        ctk.CTkButton(dlg,text="Обзор",width=80, command=browse).pack()
        msg = ctk.CTkLabel(dlg,text="",text_color="#ff0000"); msg.pack(pady=(5,0))
        def save_mapping():
            g = self.gesture_cb.get().strip(); f = entry.get().strip()
            if g not in GESTURE_OPTIONS or not f or not f.lower().endswith(('.bat','.sh')):
                msg.configure(text="Выберите жест и корректный файл")
                return
            # копируем в scripts (если файл не совпадает с уже существующим)
            dest = SCRIPTS_DIR / os.path.basename(f)
            try:
                if Path(f).resolve() != dest.resolve():
                    shutil.copy(f, dest)
            except Exception:
                pass  # игнорируем одинаковые файлы или ошибки копирования
            set_user_script(self.current_user_id, g, dest.name)
            load_user_scripts(self.current_user_id)
            dlg.destroy()
        btn_frame = ctk.CTkFrame(dlg); btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame,text="Сохранить",width=80,command=save_mapping).pack(side='left',padx=10)
        ctk.CTkButton(btn_frame,text="Отмена",width=80,command=dlg.destroy).pack(side='right',padx=10)

    def _on_logout(self): self.destroy(); main()

if __name__=='__main__':
    def main():
        app=GestureApp(); app.mainloop();
        if getattr(app,'run_recognition',False): realtime.main(app.selected_device)
    main()
