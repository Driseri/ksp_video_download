import sys
import os
from src.core.yt_dlp_handler import YtDlpHandler

def test_video_info():
    """Тестирование получения информации о видео с форматами"""
    handler = YtDlpHandler()
    
    # Тестируем на известном рабочем URL
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    
    print(f"Получение информации о видео: {url}")
    info = handler.get_video_info(url)
    
    if info:
        print("\nТест успешно пройден! Информация о видео получена.")
    else:
        print("\nТест не пройден! Не удалось получить информацию о видео.")

if __name__ == "__main__":
    test_video_info()