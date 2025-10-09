#!/usr/bin/env python3
"""
Тестовый скрипт для проверки минимального функционала yt-dlp
"""
import yt_dlp
import sys

def test_minimal_extraction(url):
    """Тест минимального извлечения информации"""
    print(f"Тестирование URL: {url}")
    print("=" * 50)
    
    # Тест 1: Самые базовые настройки
    print("Тест 1: Базовые настройки")
    ydl_opts_basic = {
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_basic) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                print(f"✓ Успех! Название: {info.get('title', 'Неизвестно')}")
                print(f"  ID: {info.get('id', 'Неизвестно')}")
                print(f"  Автор: {info.get('uploader', 'Неизвестно')}")
                return True
            else:
                print("✗ Информация не получена")
    except Exception as e:
        print(f"✗ Ошибка: {str(e)}")
    
    # Тест 2: С игнорированием ошибок
    print("\nТест 2: С игнорированием ошибок")
    ydl_opts_ignore = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_ignore) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                print(f"✓ Успех! Название: {info.get('title', 'Неизвестно')}")
                return True
            else:
                print("✗ Информация не получена")
    except Exception as e:
        print(f"✗ Ошибка: {str(e)}")
    
    # Тест 3: Только метаданные
    print("\nТест 3: Только метаданные")
    ydl_opts_meta = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'skip_download': True,
        'writeinfojson': False,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                print(f"✓ Успех! Название: {info.get('title', 'Неизвестно')}")
                return True
            else:
                print("✗ Информация не получена")
    except Exception as e:
        print(f"✗ Ошибка: {str(e)}")
    
    return False

def main():
    """Основная функция тестирования"""
    # Тестовые URL
    test_urls = [
        "https://youtu.be/8V4KalLzl9E?si=OlZKX2HD7vMEnC5m",  # Проблемный URL
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",        # Rick Roll (обычно работает)
    ]
    
    for url in test_urls:
        success = test_minimal_extraction(url)
        print(f"\nРезультат для {url}: {'✓ УСПЕХ' if success else '✗ НЕУДАЧА'}")
        print("=" * 70)

if __name__ == "__main__":
    main()