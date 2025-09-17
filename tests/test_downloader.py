#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
from unittest.mock import MagicMock, patch
import sys

# Добавление родительской директории в путь для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.downloader import VideoDownloader


class TestVideoDownloader(unittest.TestCase):
    """Тесты для класса VideoDownloader"""
    
    def setUp(self):
        self.downloader = VideoDownloader()
        self.test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.test_output_path = "./test_downloads"
    
    def tearDown(self):
        # Удаление тестовой директории, если она существует
        if os.path.exists(self.test_output_path):
            import shutil
            shutil.rmtree(self.test_output_path)
    
    def test_format_size(self):
        """Тест форматирования размера"""
        self.assertEqual(self.downloader._format_size(500), "500.00 Б")
        self.assertEqual(self.downloader._format_size(1024), "1.00 КБ")
        self.assertEqual(self.downloader._format_size(1024 * 1024), "1.00 МБ")
        self.assertEqual(self.downloader._format_size(1024 * 1024 * 1024), "1.00 ГБ")
    
    def test_format_time(self):
        """Тест форматирования времени"""
        self.assertEqual(self.downloader._format_time(30), "30 сек")
        self.assertEqual(self.downloader._format_time(90), "1 мин 30 сек")
        self.assertEqual(self.downloader._format_time(3661), "1 ч 1 мин")
    
    def test_get_format_options(self):
        """Тест получения опций формата"""
        # Тест MP3
        mp3_opts = self.downloader._get_format_options("mp3")
        self.assertEqual(mp3_opts["format"], "bestaudio/best")
        self.assertEqual(mp3_opts["postprocessors"][0]["preferredcodec"], "mp3")
        
        # Тест 720p
        p720_opts = self.downloader._get_format_options("720")
        self.assertEqual(p720_opts["format"], "bestvideo[height<=720]+bestaudio/best[height<=720]/best")
        
        # Тест best
        best_opts = self.downloader._get_format_options("best")
        self.assertEqual(best_opts["format"], "bestvideo+bestaudio/best")
    
    @patch("yt_dlp.YoutubeDL")
    def test_download(self, mock_ytdl):
        """Тест загрузки видео"""
        # Настройка мока
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        
        # Настройка возвращаемого значения extract_info
        mock_info = {"title": "Test Video", "ext": "mp4"}
        mock_instance.extract_info.return_value = mock_info
        mock_instance.prepare_filename.return_value = "Test Video.mp4"
        
        # Тестирование функции загрузки
        progress_callback = MagicMock()
        result = self.downloader.download(
            self.test_url, self.test_output_path, "best", progress_callback
        )
        
        # Проверки
        self.assertTrue(os.path.exists(self.test_output_path))
        mock_instance.extract_info.assert_called_once_with(self.test_url, download=True)
        self.assertEqual(result, os.path.join(self.test_output_path, "Test Video.mp4"))


if __name__ == "__main__":
    unittest.main()