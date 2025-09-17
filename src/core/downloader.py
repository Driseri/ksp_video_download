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
            return {
                'format': f'bestvideo[height<=720][vcodec*={video_codec}]+bestaudio/best[height<=720]/bestvideo[height<=720]+bestaudio/best',
            }
        elif format_option == "1080":
            return {
                'format': f'bestvideo[height<=1080][vcodec*={video_codec}]+bestaudio/best[height<=1080]/bestvideo[height<=1080]+bestaudio/best',
            }
        elif format_option == "480":
            return {
                'format': f'bestvideo[height<=480][vcodec*={video_codec}]+bestaudio/best[height<=480]/bestvideo[height<=480]+bestaudio/best',
            }
        else:  # best
            return {
                'format': f'bestvideo[vcodec*={video_codec}]+bestaudio/bestvideo+bestaudio/best',
            }
    
    def download(self, url: str, output_path: str, format_option: str, 
                 progress_callback: Optional[Callable[[float, str], None]] = None,
                 codec: str = "h264", referrer: str = None) -> str:
        """Загружает видео по указанному URL
        
        Args:
            url: URL видео для загрузки
            output_path: Путь для сохранения файла
            format_option: Опция формата (mp3, m4a, 720, 480, best)
            progress_callback: Функция обратного вызова для отслеживания прогресса
            codec: Кодек видео (h264 или av1)
            referrer: Referrer для HTTP-запроса (используется для Kinescope)
        """
        self.logger.info(f"Начало загрузки видео: {url}")
        self.logger.info(f"Путь сохранения: {output_path}, формат: {format_option}, кодек: {codec}")
        
        # Создание директории для загрузки, если она не существует
        os.makedirs(output_path, exist_ok=True)
        self.logger.debug(f"Директория для загрузки создана/проверена: {output_path}")
        
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
        format_opts = self._get_format_options(format_option, codec)
        ydl_opts.update(format_opts)
        
        # Добавление хука прогресса, если предоставлен колбэк
        if progress_callback:
            ydl_opts['progress_hooks'] = [self._progress_hook(progress_callback)]
        
        # Загрузка видео
        try:
            self.logger.debug(f"Настройки загрузки: {ydl_opts}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info("Извлечение информации о видео...")
                info = ydl.extract_info(url, download=True)
                
                if info:
                    # Получаем путь к загруженному файлу
                    filename = ydl.prepare_filename(info)
                    # Проверяем расширение файла, так как оно может измениться после постобработки
                    if 'ext' in info and not filename.endswith(info['ext']):
                        base_filename = os.path.splitext(filename)[0]
                        filename = f"{base_filename}.{info['ext']}"
                    
                    result_file = os.path.join(output_path, os.path.basename(filename))
                    self.logger.info(f"Загрузка завершена успешно: {result_file}")
                    return result_file
                else:
                    error_msg = "Не удалось получить информацию о видео"
                    self.logger.error(error_msg)
                    raise Exception(_("error_no_video_info"))
        except yt_dlp.utils.ExtractorError as e:
            error_msg = f"Ошибка экстрактора при загрузке видео: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            # Проверяем, если это ошибка формата, пробуем с базовым форматом
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
            
            raise Exception(_("error_download_failed"))
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"Ошибка загрузки: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(_("error_download_failed"))
        except Exception as e:
            error_msg = f"Неожиданная ошибка при загрузке видео: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(_("error_download_failed"))