#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Базовый класс для рабочих потоков приложения
"""

from PySide6.QtCore import QThread, Signal
from src.core.logger import get_logger


class BaseWorker(QThread):
    """
    Базовый класс для всех рабочих потоков приложения.
    Обеспечивает общую функциональность для отмены операций и обработки ошибок.
    """
    # Общие сигналы, которые могут использовать наследники
    error = Signal(str)
    progress_updated = Signal(float, str)
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self._is_cancelled = False
        self._resources_to_cleanup = []  # Список ресурсов для очистки
    
    def cancel(self):
        """Отменяет выполнение операции"""
        self._is_cancelled = True
        self.logger.info(f"Получен запрос на отмену операции в {self.__class__.__name__}")
    
    def stop(self):
        """Альтернативный метод для отмены (для совместимости)"""
        self.cancel()
    
    def is_cancelled(self):
        """Проверяет, была ли отменена операция"""
        return self._is_cancelled
    
    def check_cancelled(self):
        """Проверяет отмену и возвращает True, если операция отменена"""
        if self._is_cancelled:
            self.logger.info(f"Операция в {self.__class__.__name__} была отменена")
            return True
        return False
    
    def handle_error(self, error, error_message=None):
        """
        Обрабатывает ошибку и отправляет сигнал с сообщением
        
        Args:
            error: Объект исключения
            error_message: Опциональное сообщение об ошибке
        """
        message = error_message or str(error)
        self.logger.error(f"Ошибка в {self.__class__.__name__}: {message}", exc_info=True)
        self.error.emit(message)
    
    def add_resource_for_cleanup(self, resource, cleanup_method=None):
        """
        Добавляет ресурс для автоматической очистки при завершении потока
        
        Args:
            resource: Ресурс для очистки (файл, соединение, процесс и т.д.)
            cleanup_method: Метод для очистки ресурса (по умолчанию close())
        """
        if cleanup_method is None:
            cleanup_method = getattr(resource, 'close', None)
        
        if cleanup_method:
            self._resources_to_cleanup.append((resource, cleanup_method))
            self.logger.debug(f"Добавлен ресурс для очистки: {type(resource).__name__}")
    
    def cleanup_resources(self, force=False):
        """
        Очищает все зарегистрированные ресурсы
        
        Args:
            force: Если True, игнорирует ошибки и принудительно очищает все ресурсы
        """
        if not self._resources_to_cleanup:
            return
            
        cleaned_count = 0
        for resource, cleanup_method in self._resources_to_cleanup[:]:  # Копируем список
            try:
                if hasattr(resource, 'closed') and resource.closed:
                    cleaned_count += 1
                    continue  # Ресурс уже закрыт
                
                cleanup_method()
                cleaned_count += 1
                self.logger.debug(f"Ресурс {type(resource).__name__} успешно очищен")
            except Exception as e:
                if force:
                    self.logger.warning(f"Принудительная очистка ресурса {type(resource).__name__}: {e}")
                    cleaned_count += 1  # Считаем как очищенный при принудительной очистке
                else:
                    self.logger.warning(f"Ошибка при очистке ресурса {type(resource).__name__}: {e}")
        
        if force or cleaned_count == len(self._resources_to_cleanup):
            self._resources_to_cleanup.clear()
            self.logger.debug(f"Очищено {cleaned_count} ресурсов")
    
    def terminate(self):
        """Переопределяем terminate для принудительной очистки ресурсов"""
        self.logger.info(f"Принудительное завершение потока {self.__class__.__name__}")
        self._is_cancelled = True
        
        # Принудительная очистка ресурсов перед завершением
        self.cleanup_resources(force=True)
        
        # Дополнительная задержка для завершения очистки
        try:
            super().terminate()
        except Exception as e:
            self.logger.warning(f"Ошибка при завершении потока: {e}")
    
    def quit(self):
        """Переопределяем quit для корректной очистки ресурсов"""
        self.logger.info(f"Корректное завершение потока {self.__class__.__name__}")
        self.cleanup_resources()
        super().quit()
    
    def run(self):
        """Базовая реализация run с автоматической очисткой ресурсов"""
        try:
            self.work()
        except Exception as e:
            if not self.is_cancelled():
                self.handle_error(e)
        finally:
            # Очистка ресурсов в конце выполнения (если поток не был принудительно завершен)
            if not self._is_cancelled:
                self.cleanup_resources()
            else:
                # При отмене просто логируем, ресурсы уже должны быть очищены в terminate()
                self.logger.debug("Поток был отменен, ресурсы должны быть очищены в terminate()")
    
    def work(self):
        """
        Метод для переопределения в наследниках.
        Содержит основную логику работы потока.
        """
        raise NotImplementedError("Метод work() должен быть переопределен в наследнике")