#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging
import signal
import atexit
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.main_window import MainWindow
from src.core.logger import get_logger
from src.core.localization import get_localization, _


def cleanup_on_exit():
    """Функция очистки при завершении приложения"""
    logger = get_logger()
    logger.info("Выполнение очистки при завершении приложения")
    
    try:
        # Завершаем все процессы FFmpeg
        from src.core.ffmpeg_processor import FFmpegProcessor
        FFmpegProcessor.terminate_all_processes()
        
        # Завершаем все потоки через менеджер
        from src.core.thread_manager import thread_manager
        thread_manager.terminate_all_threads()
        
        logger.info("Очистка завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка при очистке: {e}")


def signal_handler(signum, frame):
    """Обработчик системных сигналов"""
    logger = get_logger()
    logger.info(f"Получен сигнал {signum}, выполняем экстренное завершение")
    
    # Выполняем очистку
    cleanup_on_exit()
    
    # Принудительно завершаем приложение
    sys.exit(1)


def setup_signal_handlers():
    """Настройка обработчиков системных сигналов"""
    # Регистрируем обработчики сигналов (только для Unix-подобных систем)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, signal_handler)
    
    # Регистрируем функцию очистки для нормального завершения
    atexit.register(cleanup_on_exit)


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
    
    # Настройка обработчиков сигналов
    setup_signal_handlers()


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