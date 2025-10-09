"""
Централизованный менеджер потоков для отслеживания и управления всеми активными потоками приложения
"""

import threading
from typing import Dict, List, Any
from PySide6.QtCore import QThread
from src.core.logger import get_logger


class ThreadManager:
    """Централизованный менеджер для отслеживания и управления всеми потоками"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.logger = get_logger()
            self._threads: Dict[str, QThread] = {}
            self._thread_lock = threading.Lock()
            self._initialized = True
    
    def register_thread(self, thread_id: str, thread: QThread, description: str = ""):
        """Регистрирует поток в менеджере"""
        with self._thread_lock:
            if thread_id in self._threads:
                self.logger.warning(f"Поток с ID '{thread_id}' уже зарегистрирован, заменяем")
            
            self._threads[thread_id] = thread
            self.logger.info(f"Зарегистрирован поток: {thread_id} ({description})")
    
    def unregister_thread(self, thread_id: str):
        """Удаляет поток из менеджера"""
        with self._thread_lock:
            if thread_id in self._threads:
                del self._threads[thread_id]
                self.logger.info(f"Поток {thread_id} удален из реестра")
            else:
                self.logger.warning(f"Попытка удалить незарегистрированный поток: {thread_id}")
    
    def get_active_threads(self) -> Dict[str, QThread]:
        """Возвращает словарь всех активных потоков"""
        with self._thread_lock:
            active_threads = {}
            for thread_id, thread in self._threads.items():
                if thread.isRunning():
                    active_threads[thread_id] = thread
            return active_threads
    
    def get_all_threads(self) -> Dict[str, QThread]:
        """Возвращает словарь всех зарегистрированных потоков"""
        with self._thread_lock:
            return self._threads.copy()
    
    def terminate_all_threads(self, timeout_ms: int = 3000) -> bool:
        """
        Принудительно завершает все активные потоки
        
        Args:
            timeout_ms: Таймаут ожидания корректного завершения в миллисекундах
            
        Returns:
            bool: True если все потоки завершены успешно, False если были проблемы
        """
        with self._thread_lock:
            if not self._threads:
                self.logger.info("Нет зарегистрированных потоков для завершения")
                return True
            
            self.logger.info(f"Начинаем завершение {len(self._threads)} зарегистрированных потоков")
            all_terminated = True
            
            # Сначала пытаемся корректно остановить потоки
            for thread_id, thread in self._threads.items():
                try:
                    if thread.isRunning():
                        self.logger.info(f"Отправка сигнала остановки потоку: {thread_id}")
                        
                        # Пытаемся вызвать метод stop(), если он есть
                        if hasattr(thread, 'stop'):
                            thread.stop()
                        
                        # Мягкое завершение
                        thread.terminate()
                        
                        # Ждем завершения
                        if thread.wait(timeout_ms):
                            self.logger.info(f"Поток {thread_id} корректно завершен")
                        else:
                            self.logger.warning(f"Поток {thread_id} не завершился за {timeout_ms}мс")
                            all_terminated = False
                    else:
                        self.logger.info(f"Поток {thread_id} уже завершен")
                        
                except Exception as e:
                    self.logger.error(f"Ошибка при завершении потока {thread_id}: {e}")
                    all_terminated = False
            
            # Принудительно завершаем оставшиеся потоки
            for thread_id, thread in self._threads.items():
                try:
                    if thread.isRunning():
                        self.logger.warning(f"Принудительное завершение потока: {thread_id}")
                        
                        # В PyQt нет метода kill(), используем terminate() повторно
                        thread.terminate()
                        
                        # Ждем еще немного
                        if not thread.wait(1000):
                            self.logger.error(f"Не удалось принудительно завершить поток: {thread_id}")
                            all_terminated = False
                        else:
                            self.logger.info(f"Поток {thread_id} принудительно завершен")
                            
                except Exception as e:
                    self.logger.error(f"Критическая ошибка при принудительном завершении {thread_id}: {e}")
                    all_terminated = False
            
            # Очищаем реестр
            self._threads.clear()
            self.logger.info("Реестр потоков очищен")
            
            return all_terminated
    
    def get_thread_info(self) -> List[Dict[str, Any]]:
        """Возвращает информацию о всех зарегистрированных потоках"""
        with self._thread_lock:
            info = []
            for thread_id, thread in self._threads.items():
                info.append({
                    'id': thread_id,
                    'running': thread.isRunning(),
                    'finished': thread.isFinished(),
                    'class_name': thread.__class__.__name__
                })
            return info
    
    def cleanup_finished_threads(self):
        """Удаляет завершенные потоки из реестра"""
        with self._thread_lock:
            finished_threads = []
            for thread_id, thread in self._threads.items():
                if thread.isFinished():
                    finished_threads.append(thread_id)
            
            for thread_id in finished_threads:
                del self._threads[thread_id]
                self.logger.info(f"Удален завершенный поток из реестра: {thread_id}")
            
            if finished_threads:
                self.logger.info(f"Очищено {len(finished_threads)} завершенных потоков")


# Глобальный экземпляр менеджера потоков
thread_manager = ThreadManager()