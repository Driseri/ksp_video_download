#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.main_window import MainWindow
from src.core.logger import get_logger
from src.core.localization import get_localization, _


def setup_environment():
    """Настройка окружения приложения"""
    # Создание директории для загрузок, если она не существует
    downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    
    # Установка текущей директории для корректной работы относительных путей
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)
    
    # Инициализация логгера
    logger = get_logger(level=logging.INFO)
    logger.info("Приложение запущено")
    
    # Инициализация локализации
    get_localization()


def main():
    """Основная функция запуска приложения"""
    setup_environment()
    logger = get_logger()
    
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(_("app_title"))
        
        window = MainWindow()
        window.show()
        
        logger.info("Приложение запущено успешно")
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()