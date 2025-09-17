#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
import sys


def run_tests():
    """Запускает все тесты в директории tests"""
    # Добавление корневой директории проекта и директории src в путь для импорта модулей
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(project_root, "src"))
    sys.path.insert(0, project_root)
    
    # Обнаружение и запуск тестов
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Запуск тестов с подробным выводом
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Возврат кода завершения в зависимости от результата тестов
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())