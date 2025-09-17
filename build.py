#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path


def clean_build_artifacts():
    """Очистка артефактов предыдущих сборок"""
    print("Очистка артефактов предыдущих сборок...")
    
    # Директории для очистки
    dirs_to_clean = ["build", "dist"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Удаление директории {dir_name}...")
            try:
                # Сначала пробуем удалить исполняемый файл, если он существует
                if dir_name == "dist":
                    exe_path = os.path.join(dir_name, "KSPVideoDownloader.exe")
                    if os.path.exists(exe_path):
                        try:
                            os.chmod(exe_path, 0o777)  # Даем полные права на файл
                            os.unlink(exe_path)
                            print(f"Удален файл {exe_path}")
                        except Exception as e:
                            print(f"Предупреждение: Не удалось удалить {exe_path}: {e}")
                            print("Попробуйте закрыть все экземпляры приложения и повторить сборку.")
                
                # Удаляем директорию
                shutil.rmtree(dir_name, ignore_errors=True)
            except Exception as e:
                print(f"Предупреждение: Не удалось полностью удалить {dir_name}: {e}")
    
    # Удаление .spec файлов
    spec_files = list(Path(".").glob("*.spec"))
    for spec_file in spec_files:
        try:
            print(f"Удаление файла спецификации {spec_file}...")
            spec_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"Предупреждение: Не удалось удалить {spec_file}: {e}")
    
    # Удаление __pycache__ директорий
    pycache_dirs = list(Path(".").rglob("__pycache__"))
    for pycache_dir in pycache_dirs:
        try:
            print(f"Удаление кэша Python {pycache_dir}...")
            shutil.rmtree(pycache_dir, ignore_errors=True)
        except Exception as e:
            print(f"Предупреждение: Не удалось удалить {pycache_dir}: {e}")
    
    print("Очистка завершена.")


def check_dependencies():
    """Проверка наличия необходимых зависимостей"""
    print("Проверка зависимостей...")
    
    # Словарь соответствия имен пакетов и модулей
    packages_to_modules = {
        "pyinstaller": "PyInstaller",
        "PySide6": "PySide6",
        "yt-dlp": "yt_dlp",
        "requests": "requests",
        "pillow": "PIL"
    }
    
    missing_packages = []
    
    for package, module in packages_to_modules.items():
        try:
            __import__(module)
            print(f"✓ {package} установлен")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} не найден")
    
    if missing_packages:
        print(f"Отсутствующие пакеты: {', '.join(missing_packages)}")
        print("Установите их командой: pip install -r requirements.txt")
        return False
    
    print("Все зависимости установлены.")
    return True


def check_resources():
    """Проверка наличия необходимых ресурсов"""
    print("Проверка ресурсов...")
    
    required_files = [
        "src/main.py",
        "resources/icon.ico",
        "resources/locales/ru.json",
        "resources/locales/en.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
            print(f"✗ {file_path} не найден")
        else:
            print(f"✓ {file_path} найден")
    
    if missing_files:
        print(f"Отсутствующие файлы: {', '.join(missing_files)}")
        return False
    
    print("Все ресурсы найдены.")
    return True


def build_app():
    """Сборка приложения с помощью PyInstaller"""
    print("=" * 50)
    print("Начинаю сборку KSP Video Downloader...")
    print("=" * 50)
    
    # Проверка зависимостей
    if not check_dependencies():
        return 1
    
    # Проверка ресурсов
    if not check_resources():
        return 1
    
    # Очистка артефактов
    clean_build_artifacts()
    
    # Имя приложения и версия
    app_name = "KSPVideoDownloader"
    version = datetime.now().strftime("%Y.%m.%d")
    
    print(f"Сборка {app_name} версии {version}...")
    
    # Команда для сборки
    cmd = [
        "pyinstaller",
        "--name", app_name,
        "--windowed",  # Без консольного окна
        "--onefile",   # Один исполняемый файл
        "--icon=resources/icon.ico",
        "--add-data", "resources;resources",
        "--clean",     # Очистка кэша PyInstaller
        "--noconfirm", # Не запрашивать подтверждение
        "--optimize", "2",  # Оптимизация байт-кода
        "--strip",     # Удаление отладочной информации (только для Linux/macOS)
        # Использование runtime-hook для исправления SSL
        "--runtime-hook=ssl_hook.py",
        # Явное включение необходимых модулей
        "--hidden-import=ssl",
        "--hidden-import=_ssl",
        "--hidden-import=cryptography",
        "--hidden-import=certifi",
        "--hidden-import=idna",
        "--hidden-import=urllib3",
        "--hidden-import=charset_normalizer",
        "--hidden-import=unicodedata",
        # Отключение оптимизаций, которые могут вызывать проблемы с DLL
        "--noupx",
        # Включение всех бинарных зависимостей
        "--collect-all", "yt_dlp",
        "--collect-all", "certifi",
        # Добавление бинарных файлов SSL
        "--add-binary", f"{sys.prefix}\\DLLs\\_ssl.pyd;.",
        "--add-binary", f"{sys.prefix}\\DLLs\\_socket.pyd;.",
        # Добавление SSL DLL файлов
        "--add-binary", f"{sys.prefix}\\Library\\bin\\libssl*.dll;.",
        "--add-binary", f"{sys.prefix}\\Library\\bin\\libcrypto*.dll;.",
        "src/main.py"
    ]
    
    # Удаление --strip для Windows
    if sys.platform == "win32":
        cmd.remove("--strip")
    
    print("Команда сборки:")
    print(" ".join(cmd))
    print()
    
    # Запуск PyInstaller
    try:
        print("Запуск PyInstaller...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("Вывод PyInstaller:")
        print(result.stdout)
        
        if result.stderr:
            print("Предупреждения:")
            print(result.stderr)
        
        # Проверка результата
        exe_path = os.path.join("dist", f"{app_name}.exe" if sys.platform == "win32" else app_name)
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # Размер в MB
            print("=" * 50)
            print("✓ Сборка успешно завершена!")
            print(f"✓ Исполняемый файл: {exe_path}")
            print(f"✓ Размер файла: {file_size:.1f} MB")
            print("=" * 50)
            return 0
        else:
            print("✗ Исполняемый файл не найден после сборки!")
            return 1
            
    except subprocess.CalledProcessError as e:
        print("=" * 50)
        print("✗ Ошибка при сборке!")
        print(f"Код ошибки: {e.returncode}")
        if e.stdout:
            print("Вывод:")
            print(e.stdout)
        if e.stderr:
            print("Ошибки:")
            print(e.stderr)
        print("=" * 50)
        return 1
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        return 1


def main():
    """Главная функция"""
    try:
        return build_app()
    except KeyboardInterrupt:
        print("\nСборка прервана пользователем.")
        return 1
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())