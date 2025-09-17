#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import locale
from typing import Dict, Any


class Localization:
    """Класс для локализации приложения"""
    
    def __init__(self, lang: str = None):
        """Инициализация локализации
        
        Args:
            lang: Код языка (ru, en, etc.). Если None, используется системный язык
        """
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_lang = lang or self._get_system_language()
        self._load_translations()
        
    def set_language(self, lang: str) -> bool:
        """Устанавливает текущий язык
        
        Возвращает True при успешной установке, иначе False
        """
        if lang in self.translations:
            self.current_lang = lang
            return True
        return False
        
    def get_available_languages(self) -> list:
        """Возвращает список доступных языков
        
        Returns:
            Список кодов языков
        """
        return list(self.translations.keys())
    
    def _get_system_language(self) -> str:
        """Определяет язык системы
        
        Returns:
            Код языка (ru, en, etc.)
        """
        try:
            system_lang, _ = locale.getdefaultlocale()
            if system_lang:
                return system_lang.split('_')[0].lower()
        except Exception:
            pass
        return 'ru'  # Русский по умолчанию
    
    def _load_translations(self) -> None:
        """Загружает переводы из файлов локализации"""
        # Директория с файлами локализации
        locales_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources', 'locales'
        )
        
        # Создаем директорию, если она не существует
        if not os.path.exists(locales_dir):
            os.makedirs(locales_dir, exist_ok=True)
        
        # Загружаем переводы для всех доступных языков
        for lang_file in os.listdir(locales_dir) if os.path.exists(locales_dir) else []:
            if lang_file.endswith('.json'):
                lang_code = os.path.splitext(lang_file)[0]
                try:
                    with open(os.path.join(locales_dir, lang_file), 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Ошибка загрузки локализации {lang_file}: {e}")
        
        # Если нет файлов локализации или текущий язык не найден, создаем базовые переводы
        if not self.translations or self.current_lang not in self.translations:
            self._create_default_translations()
    
    def _create_default_translations(self) -> None:
        """Создает файлы с базовыми переводами"""
        locales_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources', 'locales'
        )
        
        # Создаем директорию, если она не существует
        if not os.path.exists(locales_dir):
            os.makedirs(locales_dir, exist_ok=True)
        
        # Базовые переводы для русского языка
        ru_translations = {
            "app_title": "KSP Video Downloader",
            "url_label": "URL видео:",
            "format_label": "Формат:",
            "save_path_label": "Путь сохранения:",
            "browse_button": "Обзор",
            "download_button": "Загрузить",
            "cancel_button": "Отмена",
            "status_ready": "Готов к загрузке",
            "status_downloading": "Загрузка: {progress}% - {speed} - Осталось: {eta}",
            "status_complete": "Загрузка завершена: {filename}",
            "status_error": "Ошибка: {error}",
            "format_best": "Лучшее качество",
            "format_720p": "720p",
            "format_1080p": "1080p",
            "format_480p": "480p",
            "format_360p": "360p",
            "format_mp3": "MP3 (только аудио)",
            "error_invalid_url": "Неверный URL видео",
            "error_network": "Ошибка сети",
            "error_permission": "Ошибка доступа к файлу",
            "dialog_title_browse": "Выберите директорию для сохранения",
            "dialog_title_error": "Ошибка",
            "dialog_title_info": "Информация",
            "dialog_msg_complete": "Загрузка завершена успешно!",
            "language_changed": "Язык изменен. Приложение будет перезапущено для применения изменений.",
            "language_change_error": "Ошибка при смене языка. Выбранный язык недоступен.",
            "general_tab": "Общие",
            "kinescope_tab": "Kinescope",
            "language_label": "Язык:",
            "manual_input": "Ручной ввод",
            "file_input": "Загрузка из файла",
            "drag_drop_hint": "Перетащите JSON файл сюда или нажмите кнопку выбора",
            "select_file_button": "Выбрать файл",
            "referrer_label": "Referrer:",
            "video_url_label": "URL видео:",
            "filename_label": "Имя файла:",
            "codec_label": "Кодек:",
            "codec_help": "Справка по кодекам"
        }
        
        # Базовые переводы для английского языка
        en_translations = {
            "app_title": "KSP Video Downloader",
            "url_label": "Video URL:",
            "format_label": "Format:",
            "save_path_label": "Save path:",
            "browse_button": "Browse",
            "download_button": "Download",
            "cancel_button": "Cancel",
            "status_ready": "Ready to download",
            "status_downloading": "Downloading: {progress}% - {speed} - ETA: {eta}",
            "status_complete": "Download complete: {filename}",
            "status_error": "Error: {error}",
            "format_best": "Best quality",
            "format_720p": "720p",
            "format_1080p": "1080p",
            "format_480p": "480p",
            "format_360p": "360p",
            "format_mp3": "MP3 (audio only)",
            "error_invalid_url": "Invalid video URL",
            "error_network": "Network error",
            "error_permission": "File access error",
            "dialog_title_browse": "Select save directory",
            "dialog_title_error": "Error",
            "dialog_title_info": "Information",
            "dialog_msg_complete": "Download completed successfully!",
            "language_changed": "Language changed. The application will restart to apply changes.",
            "language_change_error": "Error changing language. Selected language is not available.",
            "general_tab": "General",
            "kinescope_tab": "Kinescope",
            "language_label": "Language:",
            "manual_input": "Manual input",
            "file_input": "File upload",
            "drag_drop_hint": "Drag and drop JSON file here or click select button",
            "select_file_button": "Select file",
            "referrer_label": "Referrer:",
            "video_url_label": "Video URL:",
            "filename_label": "Filename:",
            "codec_label": "Codec:",
            "codec_help": "Codec help"
        }
        
        # Сохраняем переводы в файлы
        self.translations['ru'] = ru_translations
        self.translations['en'] = en_translations
        
        try:
            with open(os.path.join(locales_dir, 'ru.json'), 'w', encoding='utf-8') as f:
                json.dump(ru_translations, f, ensure_ascii=False, indent=2)
            
            with open(os.path.join(locales_dir, 'en.json'), 'w', encoding='utf-8') as f:
                json.dump(en_translations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка создания файлов локализации: {e}")
    
    def set_language(self, lang: str) -> bool:
        """Устанавливает текущий язык. Возвращает True при успешной установке, иначе False"""
        if lang in self.translations and self.current_lang != lang:
            self.current_lang = lang
            return True
        return False
    
    def get_text(self, key: str, **kwargs: Any) -> str:
        """Возвращает локализованный текст по ключу
        
        Args:
            key: Ключ текста в файле локализации
            **kwargs: Параметры для форматирования строки
        
        Returns:
            Локализованный текст
        """
        # Получаем текст из текущего языка или из английского, если ключ не найден
        text = self.translations.get(self.current_lang, {}).get(key)
        if text is None:
            text = self.translations.get('en', {}).get(key, key)
        
        # Форматируем строку, если есть параметры
        if kwargs and isinstance(text, str):
            try:
                return text.format(**kwargs)
            except KeyError as e:
                print(f"Ошибка форматирования строки {key}: {e}")
                return text
        
        return text


# Глобальный экземпляр для использования во всем приложении
_localization = None


def get_localization() -> Localization:
    """Возвращает глобальный экземпляр локализации
    
    Returns:
        Экземпляр класса Localization
    """
    global _localization
    if _localization is None:
        _localization = Localization()
    return _localization


def _(key: str, **kwargs: Any) -> str:
    """Функция-помощник для получения локализованного текста
    
    Args:
        key: Ключ текста в файле локализации
        **kwargs: Параметры для форматирования строки
    
    Returns:
        Локализованный текст
    """
    return get_localization().get_text(key, **kwargs)