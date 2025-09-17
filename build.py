#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import shutil
from datetime import datetime


def build_app():
    """Сборка приложения с помощью PyInstaller"""
    print("Начинаю сборку приложения...")
    
    # Создание директории для сборки, если она не существует
    if not os.path.exists("build"):
        os.makedirs("build")
    
    # Очистка директории dist, если она существует
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # Имя приложения и версия
    app_name = "KSPVideoDownloader"
    version = datetime.now().strftime("%Y.%m.%d")
    
    # Команда для сборки
    cmd = [
        "pyinstaller",
        "--name", app_name,
        "--windowed",
        "--onefile",
        "--icon=resources/icon.ico" if os.path.exists("resources/icon.ico") else "",
        "--add-data", "resources;resources" if os.path.exists("resources") else "",
        "--clean",
        "src/main.py"
    ]
    
    # Удаление пустых элементов из команды
    cmd = [item for item in cmd if item]
    
    # Запуск PyInstaller
    try:
        subprocess.run(cmd, check=True)
        print(f"Сборка успешно завершена! Исполняемый файл находится в директории 'dist'.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при сборке: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(build_app())