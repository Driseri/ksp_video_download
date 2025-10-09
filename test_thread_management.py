#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы управления потоками
"""

import sys
import time
import threading
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication

# Добавляем путь к модулям
sys.path.insert(0, 'src')

from src.core.thread_manager import thread_manager
from src.core.logger import get_logger

logger = get_logger(__name__)

class TestWorker(QThread):
    """Тестовый рабочий поток"""
    progress = Signal(int)
    finished_signal = Signal(str)
    
    def __init__(self, name, duration=5):
        super().__init__()
        self.name = name
        self.duration = duration
        self._stop_requested = False
        
    def stop(self):
        """Метод для корректной остановки потока"""
        self._stop_requested = True
        
    def run(self):
        """Основная работа потока"""
        logger.info(f"Поток {self.name} начал работу")
        
        for i in range(self.duration):
            if self._stop_requested:
                logger.info(f"Поток {self.name} получил сигнал остановки")
                break
                
            time.sleep(1)
            progress_value = int((i + 1) / self.duration * 100)
            self.progress.emit(progress_value)
            logger.info(f"Поток {self.name}: прогресс {progress_value}%")
            
        if not self._stop_requested:
            logger.info(f"Поток {self.name} завершил работу естественным образом")
            self.finished_signal.emit(f"Поток {self.name} завершен")
        else:
            logger.info(f"Поток {self.name} был остановлен принудительно")
            self.finished_signal.emit(f"Поток {self.name} остановлен")

def test_thread_registration():
    """Тест регистрации и управления потоками"""
    logger.info("=== Начало тестирования системы управления потоками ===")
    
    # Создаем несколько тестовых потоков
    workers = []
    for i in range(3):
        worker = TestWorker(f"TestWorker-{i+1}", duration=10)
        workers.append(worker)
        
        # Регистрируем поток в менеджере
        thread_manager.register_thread(f"test_worker_{i+1}", worker, f"Тестовый поток {i+1}")
        
        # Запускаем поток
        worker.start()
        logger.info(f"Запущен тестовый поток {i+1}")
    
    # Показываем информацию о зарегистрированных потоках
    logger.info("=== Информация о зарегистрированных потоках ===")
    active_threads = thread_manager.get_active_threads()
    for thread_id, thread in active_threads.items():
        logger.info(f"ID: {thread_id}, Активен: {thread.isRunning()}")
    
    # Ждем немного, чтобы потоки поработали
    logger.info("Ожидание 3 секунды...")
    time.sleep(3)
    
    # Тестируем принудительное завершение всех потоков
    logger.info("=== Тестирование принудительного завершения потоков ===")
    thread_manager.terminate_all_threads()
    
    # Проверяем, что все потоки завершены
    time.sleep(2)
    logger.info("=== Проверка состояния потоков после завершения ===")
    for i, worker in enumerate(workers):
        if worker.isRunning():
            logger.error(f"ОШИБКА: Поток TestWorker-{i+1} все еще работает!")
        else:
            logger.info(f"OK: Поток TestWorker-{i+1} успешно завершен")
    
    # Проверяем, что менеджер потоков очистил реестр
    active_threads_after = thread_manager.get_active_threads()
    if active_threads_after:
        logger.error(f"ОШИБКА: В реестре остались потоки: {list(active_threads_after.keys())}")
    else:
        logger.info("OK: Реестр потоков успешно очищен")
    
    logger.info("=== Тестирование завершено ===")

if __name__ == "__main__":
    # Создаем минимальное Qt приложение для работы с потоками
    app = QApplication(sys.argv)
    
    # Запускаем тест в отдельном потоке, чтобы не блокировать Qt event loop
    test_thread = threading.Thread(target=test_thread_registration)
    test_thread.daemon = True
    test_thread.start()
    
    # Ждем завершения теста
    test_thread.join(timeout=20)  # Максимум 20 секунд
    
    logger.info("Тестирование системы управления потоками завершено")
    app.quit()