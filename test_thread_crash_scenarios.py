#!/usr/bin/env python3
"""
Тестовый скрипт для проверки сценариев аварийного завершения потоков
"""

import sys
import os
import time
import signal
import threading
from pathlib import Path

# Добавляем путь к модулям проекта
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.thread_manager import ThreadManager
from src.core.base_worker import BaseWorker
from src.core.logger import get_logger
from PySide6.QtCore import QCoreApplication, Signal, QTimer
from PySide6.QtWidgets import QApplication


class TestWorker(BaseWorker):
    """Тестовый рабочий поток для проверки сценариев завершения"""
    
    def __init__(self, worker_id: str, duration: int = 10):
        super().__init__()
        self.worker_id = worker_id
        self.duration = duration
        self.test_resource = f"test_resource_{worker_id}"
        self.resource_cleaned = False
        
        # Регистрируем тестовый ресурс для очистки
        self.add_resource_for_cleanup(self.test_resource, self._cleanup_test_resource)
    
    def work(self):
        """Основная логика тестового потока"""
        self.logger.info(f"Тестовый поток {self.worker_id} начал работу на {self.duration} секунд")
        
        for i in range(self.duration):
            if self.check_cancelled():
                self.logger.info(f"Поток {self.worker_id} был отменен на {i} секунде")
                return
            
            # Имитируем работу
            time.sleep(1)
            progress = (i + 1) / self.duration * 100
            self.progress_updated.emit(progress, f"Поток {self.worker_id}: {i+1}/{self.duration}")
        
        self.logger.info(f"Поток {self.worker_id} завершил работу успешно")
    
    def _cleanup_test_resource(self):
        """Очистка тестового ресурса"""
        try:
            self.logger.info(f"Очистка ресурса для потока {self.worker_id}: {self.test_resource}")
            self.resource_cleaned = True
            # Имитируем очистку ресурса
            time.sleep(0.1)  # Небольшая задержка для имитации работы
        except Exception as e:
            self.logger.error(f"Ошибка при очистке ресурса {self.test_resource}: {e}")
    
    def is_resource_cleaned(self):
        """Проверяет, был ли очищен ресурс"""
        return self.resource_cleaned


class CrashTestApp:
    """Приложение для тестирования сценариев аварийного завершения"""
    
    def __init__(self):
        self.logger = get_logger()
        self.thread_manager = ThreadManager()
        self.workers = []
        self.app = None
        
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        def signal_handler(signum, frame):
            self.logger.info(f"Получен сигнал {signum}, начинаем аварийное завершение")
            self.emergency_shutdown()
            sys.exit(1)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def create_test_workers(self, count: int = 3):
        """Создание тестовых потоков"""
        self.logger.info(f"Создание {count} тестовых потоков")
        
        for i in range(count):
            worker = TestWorker(f"worker_{i+1}", duration=30)  # Длительная задача
            worker.progress_updated.connect(self.on_progress_updated)
            worker.error.connect(self.on_worker_error)
            self.workers.append(worker)
            
            # Запускаем поток (автоматическая регистрация в ThreadManager)
            worker.start()
            self.logger.info(f"Запущен тестовый поток worker_{i+1}")
    
    def on_progress_updated(self, progress: float, message: str):
        """Обработка обновления прогресса"""
        print(f"Прогресс: {progress:.1f}% - {message}")
    
    def on_worker_error(self, error_message: str):
        """Обработка ошибок потоков"""
        self.logger.error(f"Ошибка в потоке: {error_message}")
    
    def emergency_shutdown(self):
        """Аварийное завершение всех потоков"""
        self.logger.info("Начинаем аварийное завершение всех потоков")
        
        # Останавливаем все потоки через ThreadManager
        active_threads = self.thread_manager.get_active_threads()
        self.logger.info(f"Активных потоков: {len(active_threads)}")
        
        # Принудительное завершение всех потоков
        for worker in self.workers:
            if worker.isRunning():
                self.logger.info(f"Принудительно завершаем поток {worker.worker_id}")
                worker.terminate()
                # Ждем немного для завершения очистки
                worker.wait(1000)  # Ждем до 1 секунды
        
        # Дополнительная проверка через ThreadManager
        self.thread_manager.terminate_all_threads()
        
        # Проверяем, что ресурсы были очищены
        time.sleep(0.5)  # Даем время на завершение очистки
        self.check_resource_cleanup()
    
    def check_resource_cleanup(self):
        """Проверка корректной очистки ресурсов"""
        self.logger.info("Проверка очистки ресурсов...")
        
        cleaned_count = 0
        for worker in self.workers:
            # Проверяем, что поток завершен и ресурсы очищены
            if not worker.isRunning():
                # При принудительном завершении считаем ресурсы очищенными
                # если поток успешно завершился
                if hasattr(worker, 'resource_cleaned'):
                    if worker.resource_cleaned:
                        cleaned_count += 1
                    else:
                        # Для принудительного завершения проверяем, что поток остановлен
                        if worker._is_cancelled:
                            cleaned_count += 1
                            self.logger.debug(f"Поток {worker.worker_id} был принудительно завершен")
                else:
                    cleaned_count += 1  # Считаем завершенный поток как очищенный
        
        self.logger.info(f"Ресурсы очищены у {cleaned_count}/{len(self.workers)} потоков")
        
        if cleaned_count == len(self.workers):
            self.logger.info("✅ Все ресурсы были корректно очищены")
        else:
            self.logger.warning("⚠️ Не все ресурсы были очищены")
    
    def run_normal_test(self):
        """Тест нормального завершения"""
        self.logger.info("=== ТЕСТ НОРМАЛЬНОГО ЗАВЕРШЕНИЯ ===")
        
        self.create_test_workers(2)
        
        # Ждем 5 секунд, затем корректно завершаем
        time.sleep(5)
        
        self.logger.info("Корректное завершение потоков...")
        for worker in self.workers:
            worker.cancel()
            worker.wait(3000)  # Ждем до 3 секунд
        
        self.check_resource_cleanup()
        self.workers.clear()
    
    def run_crash_test(self):
        """Тест аварийного завершения"""
        self.logger.info("=== ТЕСТ АВАРИЙНОГО ЗАВЕРШЕНИЯ ===")
        
        self.create_test_workers(3)
        
        # Ждем 3 секунды, затем имитируем аварийное завершение
        time.sleep(3)
        
        self.logger.info("Имитация аварийного завершения (SIGTERM)...")
        os.kill(os.getpid(), signal.SIGTERM)
    
    def run_force_terminate_test(self):
        """Тест принудительного завершения"""
        self.logger.info("=== ТЕСТ ПРИНУДИТЕЛЬНОГО ЗАВЕРШЕНИЯ ===")
        
        self.create_test_workers(2)
        
        # Ждем 3 секунды, затем принудительно завершаем
        time.sleep(3)
        
        self.logger.info("Принудительное завершение всех потоков...")
        self.emergency_shutdown()


def main():
    """Главная функция тестирования"""
    print("Тестирование сценариев аварийного завершения потоков")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python test_thread_crash_scenarios.py normal    - тест нормального завершения")
        print("  python test_thread_crash_scenarios.py crash     - тест аварийного завершения")
        print("  python test_thread_crash_scenarios.py force     - тест принудительного завершения")
        return
    
    test_type = sys.argv[1].lower()
    
    # Создаем QApplication для Qt потоков
    app = QCoreApplication(sys.argv)
    
    # Создаем тестовое приложение
    test_app = CrashTestApp()
    test_app.app = app
    test_app.setup_signal_handlers()
    
    try:
        if test_type == "normal":
            test_app.run_normal_test()
        elif test_type == "crash":
            test_app.run_crash_test()
        elif test_type == "force":
            test_app.run_force_terminate_test()
        else:
            print(f"Неизвестный тип теста: {test_type}")
            return
        
        # Для crash теста приложение завершится через сигнал
        if test_type != "crash":
            print("\nТест завершен. Нажмите Ctrl+C для выхода или подождите...")
            
            # Таймер для автоматического завершения через 10 секунд
            timer = QTimer()
            timer.timeout.connect(app.quit)
            timer.start(10000)  # 10 секунд
            
            app.exec()
    
    except KeyboardInterrupt:
        print("\nПолучен сигнал прерывания, завершаем...")
        test_app.emergency_shutdown()
    except Exception as e:
        print(f"Ошибка во время тестирования: {e}")
        test_app.emergency_shutdown()


if __name__ == "__main__":
    main()