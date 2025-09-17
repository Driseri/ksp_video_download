#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


def get_executable_dir():
    """Получает директорию исполняемого файла или скрипта"""
    if getattr(sys, 'frozen', False):
        # Если приложение собрано в exe
        return os.path.dirname(sys.executable)
    else:
        # Если запускается как скрипт
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Logger:
    """Класс для настройки логирования в приложении"""
    
    def __init__(self, name="ksp_video_downloader", level=logging.INFO):
        """Инициализация логгера
        
        Args:
            name: Имя логгера
            level: Уровень логирования
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Если обработчики уже добавлены, не добавляем новые
        if self.logger.handlers:
            return
        
        # Создаем директорию для логов в папке с исполняемым файлом
        logs_dir = os.path.join(get_executable_dir(), 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Обработчик для вывода в файл с ротацией
        log_file = os.path.join(
            logs_dir,
            f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 МБ
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        # Обработчик для вывода в консоль
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        
        # Добавляем обработчики к логгеру
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self):
        """Возвращает настроенный логгер
        
        Returns:
            Экземпляр логгера
        """
        return self.logger


# Глобальный экземпляр логгера для использования во всем приложении
_logger = None


def get_logger(name="ksp_video_downloader", level=logging.INFO):
    """Возвращает глобальный экземпляр логгера
    
    Args:
        name: Имя логгера
        level: Уровень логирования
    
    Returns:
        Экземпляр логгера
    """
    global _logger
    if _logger is None:
        _logger = Logger(name, level).get_logger()
    return _logger