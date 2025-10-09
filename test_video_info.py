#!/usr/bin/env python3
"""
Тестовый скрипт для проверки расширенной функциональности получения информации о видео
"""
import sys
sys.path.append('src')
from core.yt_dlp_handler import YtDlpHandler

def main():
    """Основная функция тестирования"""
    # Создаем экземпляр обработчика
    handler = YtDlpHandler()
    
    # Тестовые URL
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Известное рабочее видео
    ]
    
    # Тестируем получение информации
    for url in test_urls:
        print(f"\nТестирование URL: {url}")
        info = handler.get_video_info(url)
        
        if not info:
            print("❌ Не удалось получить информацию о видео")
            continue
            
        # Информация уже выводится в консоль в методе _print_video_info
        
        # Проверяем наличие форматов
        formats = info.get('formats', [])
        print(f"\nПолучено {len(formats)} форматов")
        
        # Выводим дополнительную информацию
        print("\nДополнительная информация:")
        print(f"Канал ID: {info.get('channel_id', 'Н/Д')}")
        print(f"URL канала: {info.get('channel_url', 'Н/Д')}")
        print(f"Лайки: {info.get('like_count', 'Н/Д')}")
        print(f"Дизлайки: {info.get('dislike_count', 'Н/Д')}")
        print(f"Рейтинг: {info.get('average_rating', 'Н/Д')}")
        
        # Проверяем статус лайв-трансляции
        if info.get('is_live'):
            print("Это прямая трансляция!")
        elif info.get('was_live'):
            print("Это запись прямой трансляции")

if __name__ == "__main__":
    main()