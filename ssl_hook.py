#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Runtime hook для исправления проблем с SSL библиотеками в PyInstaller
"""

import os
import sys
import importlib.util
import importlib.machinery
import ctypes
from pathlib import Path


def fix_ssl_paths():
    """
    Исправляет пути к SSL библиотекам для корректной работы в упакованном приложении
    """
    print("Применение SSL hook...")
    
    # Получаем базовый путь к приложению
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    # Добавляем базовый путь в sys.path, если его там еще нет
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    
    # Пытаемся загрузить SSL библиотеки напрямую
    try:
        # Для Windows пытаемся загрузить DLL напрямую
        if sys.platform == 'win32':
            # Ищем все DLL файлы в директории приложения
            dll_dir = Path(base_dir)
            ssl_dlls = list(dll_dir.glob("*ssl*.dll")) + list(dll_dir.glob("*crypto*.dll"))
            
            for dll_path in ssl_dlls:
                try:
                    ctypes.CDLL(str(dll_path))
                    print(f"Загружена библиотека: {dll_path}")
                except Exception as e:
                    print(f"Не удалось загрузить {dll_path}: {e}")
    
    except Exception as e:
        print(f"Ошибка при загрузке SSL библиотек: {e}")
    
    print("SSL hook применен")


# Применяем исправление при импорте этого модуля
fix_ssl_paths()