#!/usr/bin/env python3
"""
Тестовый скрипт для проверки обновленного минимального функционала yt-dlp
"""
import yt_dlp
import sys

def test_info_only_extraction(url):
    """Тест извлечения только информации без форматов"""
    print(f"Тестирование URL: {url}")
    print("=" * 50)
    
    # Тест: Только метаданные без указания формата
    print("Тест: Только метаданные (без формата)")
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': False,
        'ignoreerrors': True,
        # НЕ указываем format
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                print(f"✓ Успех! Название: {info.get('title', 'Неизвестно')}")
                print(f"  ID: {info.get('id', 'Неизвестно')}")
                print(f"  Автор: {info.get('uploader', info.get('channel', 'Неизвестно'))}")
                print(f"  Длительность: {info.get('duration', 0)} сек")
                print(f"  Просмотры: {info.get('view_count', 0)}")
                return True
            else:
                print("✗ Информация не получена")
    except Exception as e:
        print(f"✗ Ошибка: {str(e)}")
    
    return False

def test_with_handler():
    """Тест с использованием нашего обработчика"""
    print("\n" + "=" * 70)
    print("ТЕСТ С НАШИМ ОБРАБОТЧИКОМ")
    print("=" * 70)
    
    # Импортируем наш обработчик
    sys.path.append('src')
    from core.yt_dlp_handler import YtDlpHandler
    
    handler = YtDlpHandler()
    
    test_urls = [
        "https://youtu.be/8V4KalLzl9E?si=OlZKX2HD7vMEnC5m",  # Проблемный URL
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",        # Rick Roll
    ]
    
    for url in test_urls:
        print(f"\nТестирование: {url}")
        info = handler.get_video_info(url)
        if info:
            print(f"✓ Успех!")
            print(f"  Название: {info.get('title', 'Неизвестно')}")
            print(f"  ID: {info.get('id', 'Неизвестно')}")
            print(f"  Автор: {info.get('uploader', 'Неизвестно')}")
            print(f"  Описание: {info.get('description', 'Нет')[:50]}...")
        else:
            print("✗ Не удалось получить информацию")

def main():
    """Основная функция тестирования"""
    # Тестовые URL
    test_urls = [
        "https://youtu.be/8V4KalLzl9E?si=OlZKX2HD7vMEnC5m",  # Проблемный URL
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",        # Rick Roll
    ]
    
    for url in test_urls:
        success = test_info_only_extraction(url)
        print(f"\nРезультат для {url}: {'✓ УСПЕХ' if success else '✗ НЕУДАЧА'}")
        print("=" * 70)
    
    # Тест с нашим обработчиком
    test_with_handler()

if __name__ == "__main__":
    main()