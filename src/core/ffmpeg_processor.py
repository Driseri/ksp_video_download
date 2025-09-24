#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import json
import re
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from src.core.logger import get_logger
from src.core.localization import get_localization, _


class FFmpegProcessor:
    """Класс для работы с ffmpeg - обработка аудио и видео файлов"""
    
    def __init__(self):
        self.logger = get_logger()
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
        
    def _find_ffmpeg(self) -> Optional[str]:
        """Поиск исполняемого файла ffmpeg в системе"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return 'ffmpeg'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Поиск в стандартных путях Windows
        possible_paths = [
            'C:\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        return None
    
    def _find_ffprobe(self) -> Optional[str]:
        """Поиск исполняемого файла ffprobe в системе"""
        try:
            result = subprocess.run(['ffprobe', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return 'ffprobe'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Поиск в стандартных путях Windows
        possible_paths = [
            'C:\\ffmpeg\\bin\\ffprobe.exe',
            'C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe',
            'C:\\Program Files (x86)\\ffmpeg\\bin\\ffprobe.exe'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        return None
    
    def is_available(self) -> bool:
        """Проверка доступности ffmpeg и ffprobe"""
        return self.ffmpeg_path is not None and self.ffprobe_path is not None
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Получение информации о медиафайле"""
        if not self.ffprobe_path:
            raise RuntimeError(_("ffprobe_not_found"))
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(_("file_not_found").format(file=file_path))
        
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise RuntimeError(_("ffprobe_error").format(error=result.stderr))
            
            data = json.loads(result.stdout)
            
            # Извлекаем полезную информацию
            info = {
                'duration': float(data.get('format', {}).get('duration', 0)),
                'size': int(data.get('format', {}).get('size', 0)),
                'format_name': data.get('format', {}).get('format_name', ''),
                'video_streams': [],
                'audio_streams': []
            }
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    info['video_streams'].append({
                        'codec': stream.get('codec_name', ''),
                        'width': stream.get('width', 0),
                        'height': stream.get('height', 0),
                        'fps': self._parse_fps(stream.get('r_frame_rate', '0/1')),
                        'bitrate': int(stream.get('bit_rate', 0))
                    })
                elif stream.get('codec_type') == 'audio':
                    info['audio_streams'].append({
                        'codec': stream.get('codec_name', ''),
                        'sample_rate': int(stream.get('sample_rate', 0)),
                        'channels': stream.get('channels', 0),
                        'bitrate': int(stream.get('bit_rate', 0))
                    })
            
            return info
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(_("ffprobe_timeout"))
        except json.JSONDecodeError:
            raise RuntimeError(_("ffprobe_json_error"))
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о файле: {str(e)}")
            raise RuntimeError(_("ffprobe_general_error").format(error=str(e)))
    
    def _parse_fps(self, fps_string: str) -> float:
        """Парсинг FPS из строки вида '30/1'"""
        try:
            if '/' in fps_string:
                num, den = fps_string.split('/')
                return float(num) / float(den) if float(den) != 0 else 0
            return float(fps_string)
        except:
            return 0
    
    def extract_audio(self, input_file: str, output_file: str, 
                     format_type: str = 'mp3', quality: str = '192k',
                     progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Извлечение аудио из видеофайла"""
        if not self.ffmpeg_path:
            self.logger.error("FFmpeg не найден в системе")
            raise RuntimeError(_("ffmpeg_not_found"))
        
        self.logger.info(f"Начало извлечения аудио из файла: {input_file}")
        self.logger.info(f"Выходной файл: {output_file}")
        self.logger.info(f"Формат: {format_type}, качество: {quality}")
        
        try:
            # Проверяем существование входного файла
            if not os.path.exists(input_file):
                self.logger.error(f"Входной файл не найден: {input_file}")
                raise FileNotFoundError(_("file_not_found").format(file=input_file))
            
            # Получаем информацию о файле для логирования
            try:
                file_info = self.get_file_info(input_file)
                self.logger.info(f"Информация о входном файле - Длительность: {file_info.get('duration', 0):.2f}с, "
                               f"Размер: {file_info.get('size', 0)} байт")
            except Exception as e:
                self.logger.warning(f"Не удалось получить информацию о файле: {e}")
            
            # Определяем параметры кодирования в зависимости от формата
            codec_params = self._get_audio_codec_params(format_type, quality)
            self.logger.debug(f"Параметры кодека: {codec_params}")
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_file,
                '-vn',  # Без видео
                '-y',   # Перезаписать выходной файл
            ] + codec_params + [output_file]
            
            self.logger.info(f"Команда извлечения аудио: {' '.join(cmd)}")
            
            result = self._run_ffmpeg_with_progress(cmd, input_file, progress_callback)
            
            if result:
                # Проверяем результат
                if os.path.exists(output_file):
                    output_size = os.path.getsize(output_file)
                    self.logger.info(f"Извлечение аудио завершено успешно. Размер выходного файла: {output_size} байт")
                else:
                    self.logger.error("Выходной файл не был создан")
                    return False
            else:
                self.logger.error("FFmpeg вернул ошибку при извлечении аудио")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения аудио: {str(e)}")
            raise RuntimeError(_("audio_extraction_error").format(error=str(e)))
    
    def extract_video(self, input_file: str, output_file: str,
                     progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Извлечение видео без аудио"""
        if not self.ffmpeg_path:
            self.logger.error("FFmpeg не найден в системе")
            raise RuntimeError(_("ffmpeg_not_found"))
        
        self.logger.info(f"Начало извлечения видео из файла: {input_file}")
        self.logger.info(f"Выходной файл: {output_file}")
        
        try:
            # Проверяем существование входного файла
            if not os.path.exists(input_file):
                self.logger.error(f"Входной файл не найден: {input_file}")
                raise FileNotFoundError(_("file_not_found").format(file=input_file))
            
            # Получаем информацию о файле для логирования
            try:
                file_info = self.get_file_info(input_file)
                self.logger.info(f"Информация о входном файле - Длительность: {file_info.get('duration', 0):.2f}с, "
                               f"Разрешение: {file_info.get('width', 0)}x{file_info.get('height', 0)}, "
                               f"Размер: {file_info.get('size', 0)} байт")
            except Exception as e:
                self.logger.warning(f"Не удалось получить информацию о файле: {e}")
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_file,
                '-an',  # Без аудио
                '-c:v', 'copy',  # Копировать видеопоток без перекодировки
                '-y',   # Перезаписать выходной файл
                output_file
            ]
            
            self.logger.info(f"Команда извлечения видео: {' '.join(cmd)}")
            
            result = self._run_ffmpeg_with_progress(cmd, input_file, progress_callback)
            
            if result:
                # Проверяем результат
                if os.path.exists(output_file):
                    output_size = os.path.getsize(output_file)
                    self.logger.info(f"Извлечение видео завершено успешно. Размер выходного файла: {output_size} байт")
                else:
                    self.logger.error("Выходной файл не был создан")
                    return False
            else:
                self.logger.error("FFmpeg вернул ошибку при извлечении видео")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения видео: {str(e)}")
            raise RuntimeError(_("video_extraction_error").format(error=str(e)))
    
    def convert_file(self, input_file: str, output_file: str, options: Dict[str, Any],
                    progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Конвертация медиафайла с заданными параметрами"""
        if not self.ffmpeg_path:
            raise RuntimeError(_("ffmpeg_not_found"))
        
        try:
            cmd = [self.ffmpeg_path, '-i', input_file]
            
            # Добавляем параметры видео
            if 'video_codec' in options:
                cmd.extend(['-c:v', options['video_codec']])
            
            if 'video_bitrate' in options:
                cmd.extend(['-b:v', options['video_bitrate']])
            
            if 'resolution' in options and options['resolution'] != 'original':
                cmd.extend(['-s', options['resolution']])
            
            # Добавляем параметры аудио
            if 'audio_codec' in options:
                cmd.extend(['-c:a', options['audio_codec']])
            
            if 'audio_bitrate' in options:
                cmd.extend(['-b:a', options['audio_bitrate']])
            
            # Дополнительные параметры
            if 'preset' in options:
                cmd.extend(['-preset', options['preset']])
            
            if 'crf' in options:
                cmd.extend(['-crf', str(options['crf'])])
            
            cmd.extend(['-y', output_file])
            
            self.logger.info(f"Команда конвертации: {' '.join(cmd)}")
            
            return self._run_ffmpeg_with_progress(cmd, input_file, progress_callback)
            
        except Exception as e:
            self.logger.error(f"Ошибка конвертации файла: {str(e)}")
            raise RuntimeError(_("conversion_error").format(error=str(e)))
    
    def _get_audio_codec_params(self, format_type: str, quality: str) -> list:
        """Получение параметров аудиокодека"""
        params = []
        
        if format_type.lower() == 'mp3':
            params.extend(['-c:a', 'libmp3lame', '-b:a', quality])
        elif format_type.lower() == 'aac':
            params.extend(['-c:a', 'aac', '-b:a', quality])
        elif format_type.lower() == 'flac':
            params.extend(['-c:a', 'flac'])
        elif format_type.lower() == 'wav':
            params.extend(['-c:a', 'pcm_s16le'])
        else:
            # По умолчанию MP3
            params.extend(['-c:a', 'libmp3lame', '-b:a', quality])
        
        return params
    
    def _run_ffmpeg_with_progress(self, cmd: list, input_file: str,
                                 progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Запуск ffmpeg с отслеживанием прогресса"""
        process = None
        try:
            # Получаем длительность файла для расчета прогресса
            total_duration = 0
            try:
                file_info = self.get_file_info(input_file)
                total_duration = file_info.get('duration', 0)
                self.logger.debug(f"Общая длительность файла: {total_duration}с")
            except Exception as e:
                self.logger.warning(f"Не удалось получить длительность файла: {e}")
            
            # Валидация команды
            if not cmd or len(cmd) < 3:
                raise ValueError("Некорректная команда FFmpeg")
            
            self.logger.debug(f"Запуск процесса FFmpeg: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Читаем вывод ffmpeg для отслеживания прогресса
            stderr_output = []
            while True:
                try:
                    output = process.stderr.readline()
                    if output == '' and process.poll() is not None:
                        break
                    
                    if output:
                        stderr_output.append(output.strip())
                        
                        if progress_callback and total_duration > 0:
                            # Ищем время обработки в выводе ffmpeg
                            time_match = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', output)
                            if time_match:
                                try:
                                    hours = int(time_match.group(1))
                                    minutes = int(time_match.group(2))
                                    seconds = float(time_match.group(3))
                                    current_time = hours * 3600 + minutes * 60 + seconds
                                    
                                    progress = min((current_time / total_duration) * 100, 100)
                                    status = _("processing_progress").format(progress=f"{progress:.1f}")
                                    progress_callback(progress, status)
                                except (ValueError, ZeroDivisionError) as e:
                                    self.logger.debug(f"Ошибка парсинга прогресса: {e}")
                                    
                except Exception as e:
                    self.logger.warning(f"Ошибка чтения вывода FFmpeg: {e}")
                    break
            
            return_code = process.poll()
            
            if return_code == 0:
                if progress_callback:
                    progress_callback(100, _("processing_complete"))
                self.logger.debug("FFmpeg завершился успешно")
                return True
            else:
                # Собираем полный вывод ошибки
                remaining_stderr = process.stderr.read()
                if remaining_stderr:
                    stderr_output.append(remaining_stderr.strip())
                
                error_output = '\n'.join(stderr_output[-10:])  # Последние 10 строк
                self.logger.error(f"FFmpeg завершился с кодом {return_code}: {error_output}")
                raise RuntimeError(_("ffmpeg_process_error").format(error=error_output))
                
        except subprocess.TimeoutExpired:
            self.logger.error("Превышено время ожидания выполнения FFmpeg")
            if process:
                process.kill()
            raise RuntimeError(_("ffmpeg_timeout_error"))
        except Exception as e:
            self.logger.error(f"Ошибка выполнения ffmpeg: {str(e)}")
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            raise
    
    def get_supported_formats(self) -> Dict[str, list]:
        """Получение списка поддерживаемых форматов"""
        return {
            'video_formats': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'],
            'audio_formats': ['mp3', 'aac', 'flac', 'wav', 'ogg'],
            'video_codecs': ['libx264', 'libx265', 'libaom-av1', 'libvpx-vp9'],
            'audio_codecs': ['aac', 'libmp3lame', 'flac', 'pcm_s16le']
        }
    
    def get_quality_presets(self) -> Dict[str, Dict[str, Any]]:
        """Получение предустановок качества"""
        return {
            'high': {
                'video_bitrate': '8000k',
                'audio_bitrate': '320k',
                'preset': 'slow',
                'crf': 18
            },
            'medium': {
                'video_bitrate': '4000k',
                'audio_bitrate': '192k',
                'preset': 'medium',
                'crf': 23
            },
            'low': {
                'video_bitrate': '2000k',
                'audio_bitrate': '128k',
                'preset': 'fast',
                'crf': 28
            }
        }