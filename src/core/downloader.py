#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from typing import Callable, Optional, Tuple, Dict, Any

import yt_dlp

from src.core.logger import get_logger
from src.core.localization import get_localization, _


class VideoDownloader:
    """Класс для загрузки видео с использованием yt-dlp"""
    
    def __init__(self):
        self.ydl_opts = {}
        self.current_download = None
        self.logger = get_logger()
    
    def _progress_hook(self, progress_callback: Callable[[float, str], None]) -> Callable:
        """Создает функцию-хук для отслеживания прогресса загрузки"""
        def hook(d: Dict[str, Any]) -> None:
            if d['status'] == 'downloading':
                # Получение процента загрузки
                if 'total_bytes' in d and d['total_bytes'] > 0:
                    percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                    percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                else:
                    percent = 0
                
                # Получение скорости загрузки
                speed = d.get('speed', 0)
                if speed:
                    speed_str = self._format_size(speed) + '/s'
                else:
                    speed_str = 'Неизвестно'
                
                # Получение оставшегося времени
                eta = d.get('eta', 0)
                if eta:
                    eta_str = self._format_time(eta)
                else:
                    eta_str = 'Неизвестно'
                
                # Формирование статуса
                filename = os.path.basename(d['filename'])
                status = _("status_downloading").format(
                    progress=f"{percent:.1f}", 
                    speed=speed_str, 
                    eta=eta_str
                )
                
                # Вызов колбэка с прогрессом
                progress_callback(percent, status)
            
            elif d['status'] == 'finished':
                filename = os.path.basename(d['filename'])
                self.logger.info(f"Загрузка файла завершена: {filename}. Начало обработки.")
                progress_callback(100, _("status_processing").format(filename=filename))
            
            elif d['status'] == 'error':
                error_msg = d.get('error', 'Неизвестная ошибка')
                self.logger.error(f"Ошибка загрузки: {error_msg}")
                progress_callback(0, _("status_error").format(error=error_msg))
        
        return hook
    
    def _format_size(self, bytes_: int) -> str:
        """Форматирует размер в байтах в человекочитаемый формат"""
        # Используем локализованные единицы измерения
        units = [_("unit_bytes"), _("unit_kb"), _("unit_mb"), _("unit_gb"), _("unit_tb")]
        for unit in units:
            if bytes_ < 1024.0:
                return f"{bytes_:.2f} {unit}"
            bytes_ /= 1024.0
        return f"{bytes_:.2f} {_("unit_pb")}"
    
    def _format_time(self, seconds: int) -> str:
        """Форматирует время в секундах в человекочитаемый формат"""
        if seconds < 60:
            return _("time_seconds").format(seconds=seconds)
        elif seconds < 3600:
            minutes, seconds = divmod(seconds, 60)
            return _("time_minutes_seconds").format(minutes=minutes, seconds=seconds)
        else:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return _("time_hours_minutes").format(hours=hours, minutes=minutes)
    
    def _get_format_options(self, format_option: str, codec: str = "h264") -> Dict[str, Any]:
        """Возвращает опции yt-dlp в зависимости от выбранного формата и кодека
        
        Args:
            format_option: Опция формата (mp3, m4a, 720, 480, best)
            codec: Кодек видео (h264 или av1)
        """
        # Определяем кодек для видео форматов
        video_codec = "avc" if codec == "h264" else "av01"
        
        if format_option == "mp3":
            return {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        elif format_option == "m4a":
            return {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '192',
                }],
            }
        elif format_option == "720":
            # Более гибкий подход с fallback опциями
            return {
                'format': f'bestvideo[height<=720][vcodec*={video_codec}]+bestaudio/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            }
        elif format_option == "1080":
            return {
                'format': f'bestvideo[height<=1080][vcodec*={video_codec}]+bestaudio/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            }
        elif format_option == "480":
            return {
                'format': f'bestvideo[height<=480][vcodec*={video_codec}]+bestaudio/bestvideo[height<=480]+bestaudio/best[height<=480]/best',
            }
        elif format_option == "360":
            return {
                'format': f'bestvideo[height<=360][vcodec*={video_codec}]+bestaudio/bestvideo[height<=360]+bestaudio/best[height<=360]/best',
            }
        else:  # best
            return {
                'format': f'bestvideo[vcodec*={video_codec}]+bestaudio/bestvideo+bestaudio/best',
            }
    

    

    
    def download(self, url: str, output_path: str, format_option: str = "720", 
                 codec: str = "h264", progress_callback: Callable[[float, str], None] = None, 
                 referrer: str = None) -> str:
        """
        Загружает видео с указанного URL
        
        Args:
            url: URL видео для загрузки
            output_path: Путь для сохранения файла
            format_option: Опция формата (mp3, m4a, 720, 480, best)
            progress_callback: Функция обратного вызова для отслеживания прогресса
            codec: Кодек видео (h264 или av1)
            referrer: Referrer для HTTP-запроса (используется для Kinescope)
        """
        # Валидация входных параметров
        if not url or not url.strip():
            raise ValueError("URL не может быть пустым")
            
        if not output_path or not output_path.strip():
            raise ValueError("Путь для сохранения не может быть пустым")
            
        url = url.strip()
        output_path = output_path.strip()
        
        self.logger.info(f"Начало загрузки видео: {url}")
        self.logger.info(f"Путь сохранения: {output_path}, формат: {format_option}, кодек: {codec}")
        
        # Проверка и создание директории для загрузки
        try:
            if not os.path.exists(output_path):
                os.makedirs(output_path, exist_ok=True)
                self.logger.debug(f"Директория для загрузки создана: {output_path}")
            elif not os.path.isdir(output_path):
                raise ValueError(f"Указанный путь не является директорией: {output_path}")
            elif not os.access(output_path, os.W_OK):
                raise PermissionError(f"Нет прав на запись в директорию: {output_path}")
            else:
                self.logger.debug(f"Директория для загрузки проверена: {output_path}")
        except OSError as e:
            error_msg = f"Не удалось создать или получить доступ к директории {output_path}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Базовые опции
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Добавляем HTTP-заголовки, если указан referrer (для Kinescope)
        if referrer:
            ydl_opts['http_headers'] = {
                'Referer': referrer,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        
        # Добавление опций формата с учетом кодека
        try:
            format_opts = self._get_format_options(format_option, codec)
            ydl_opts.update(format_opts)
        except Exception as e:
            error_msg = f"Ошибка при настройке формата: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Добавление хука прогресса, если предоставлен колбэк
        if progress_callback:
            ydl_opts['progress_hooks'] = [self._progress_hook(progress_callback)]
        
        # Загрузка видео
        try:
            self.logger.debug(f"Настройки загрузки: {ydl_opts}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info("Извлечение информации о видео...")
                
                # Сначала извлекаем информацию без загрузки для проверки
                try:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        raise Exception("Не удалось получить информацию о видео")
                    
                    # Проверяем доступность видео
                    if info.get('is_live'):
                        raise Exception("Загрузка прямых трансляций не поддерживается")
                        
                    if info.get('duration', 0) > 7200:  # 2 часа
                        self.logger.warning(f"Видео очень длинное ({info.get('duration')} секунд)")
                        
                except yt_dlp.utils.ExtractorError as e:
                    error_str = str(e)
                    if "Video unavailable" in error_str or "Private video" in error_str:
                        raise Exception("Видео недоступно или является приватным")
                    elif "This video is not available" in error_str:
                        raise Exception("Видео не найдено или удалено")
                    elif "Sign in to confirm your age" in error_str or "age" in error_str.lower():
                        # Специальная обработка для возрастных ограничений
                        error_msg = ("Видео имеет возрастные ограничения. Попробуйте:\n"
                                   "1. Войти в YouTube в любом браузере (Chrome, Edge, Firefox)\n"
                                   "2. Подтвердить возраст в настройках аккаунта\n"
                                   "3. Повторить загрузку\n"
                                   "Для просмотра возрастного контента войдите в YouTube в браузере")
                        self.logger.error(f"Возрастные ограничения: {error_str}")
                        raise Exception(error_msg)
                    else:
                        raise Exception(f"Ошибка при получении информации о видео: {error_str}")
                
                # Теперь загружаем видео
                info = ydl.extract_info(url, download=True)
                
                if info:
                    # Получаем путь к загруженному файлу
                    filename = ydl.prepare_filename(info)
                    # Проверяем расширение файла, так как оно может измениться после постобработки
                    if 'ext' in info and not filename.endswith(info['ext']):
                        base_filename = os.path.splitext(filename)[0]
                        filename = f"{base_filename}.{info['ext']}"
                    
                    result_file = os.path.join(output_path, os.path.basename(filename))
                    
                    # Проверяем, что файл действительно создан
                    if not os.path.exists(result_file):
                        # Ищем файл с похожим именем
                        base_name = os.path.splitext(os.path.basename(filename))[0]
                        for file in os.listdir(output_path):
                            if file.startswith(base_name):
                                result_file = os.path.join(output_path, file)
                                break
                        else:
                            raise Exception("Загруженный файл не найден")
                    
                    self.logger.info(f"Загрузка завершена успешно: {result_file}")
                    return result_file
                else:
                    error_msg = "Не удалось получить информацию о видео"
                    self.logger.error(error_msg)
                    raise Exception("Не удалось получить информацию о видео")
                    
        except yt_dlp.utils.ExtractorError as e:
            error_msg = f"Ошибка экстрактора при загрузке видео: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Проверяем специфичные ошибки
            if "Requested format is not available" in str(e):
                self.logger.warning("Попытка загрузки с базовым форматом...")
                try:
                    # Пробуем с простым форматом best
                    ydl_opts_fallback = ydl_opts.copy()
                    ydl_opts_fallback['format'] = 'best'
                    
                    with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if info:
                            filename = ydl.prepare_filename(info)
                            if 'ext' in info and not filename.endswith(info['ext']):
                                base_filename = os.path.splitext(filename)[0]
                                filename = f"{base_filename}.{info['ext']}"
                            
                            result_file = os.path.join(output_path, os.path.basename(filename))
                            self.logger.info(f"Загрузка завершена успешно (fallback): {result_file}")
                            return result_file
                except Exception as fallback_e:
                    self.logger.error(f"Fallback загрузка также не удалась: {str(fallback_e)}")
                    
            # Обработка других типов ошибок экстрактора
            error_str = str(e)
            if "Video unavailable" in error_str:
                raise Exception("Видео недоступно")
            elif "Private video" in error_str:
                raise Exception("Видео является приватным")
            elif "This video is not available" in error_str:
                raise Exception("Видео не найдено")
            elif "Sign in to confirm your age" in error_str or "age" in error_str.lower() or "restricted" in error_str.lower():
                # Специальная обработка для возрастных ограничений
                error_msg = ("Видео имеет возрастные ограничения. Для решения проблемы:\n"
                           "1. Войдите в YouTube в любом браузере (Chrome, Edge, Firefox)\n"
                           "2. Подтвердите возраст в настройках аккаунта\n"
                           "3. Повторите загрузку")
                self.logger.error(f"Возрастные ограничения: {error_str}")
                raise Exception(error_msg)
            elif "authentication" in error_str.lower():
                error_msg = ("Ошибка аутентификации. Попробуйте:\n"
                           "1. Войти в YouTube в браузере\n"
                           "2. Повторить загрузку")
                self.logger.error(f"Ошибка аутентификации: {error_str}")
                raise Exception(error_msg)
            else:
                raise Exception(f"Ошибка при загрузке видео: {error_str}")
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"Ошибка загрузки: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            if "HTTP Error 403" in str(e):
                raise Exception("Доступ к видео запрещен (HTTP 403)")
            elif "HTTP Error 404" in str(e):
                raise Exception("Видео не найдено (HTTP 404)")
            elif "Connection" in str(e):
                raise Exception("Ошибка соединения с сервером")
            else:
                raise Exception("Ошибка при загрузке видео")
                
        except ValueError as e:
            self.logger.error(f"Ошибка валидации: {str(e)}")
            raise e
            
        except PermissionError as e:
            self.logger.error(f"Ошибка доступа: {str(e)}")
            raise e
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка при загрузке видео: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception("Неожиданная ошибка при загрузке видео")