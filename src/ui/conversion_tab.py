#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QFileDialog, QMessageBox, QFrame,
    QCheckBox, QSlider, QSpinBox, QGroupBox, QDialog, QTextEdit,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, QThread

from src.core.ffmpeg_processor import FFmpegProcessor
from src.core.logger import get_logger
from src.core.localization import get_localization, _


class ConversionWorker(QThread):
    """Рабочий поток для конвертации файлов"""
    progress_updated = Signal(float, str)
    processing_finished = Signal(bool, str)
    error = Signal(str)
    
    def __init__(self, input_file: str, output_file: str, conversion_options: Dict[str, Any]):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.conversion_options = conversion_options
        self.processor = FFmpegProcessor()
        self.logger = get_logger()
        self.localization = get_localization()
    
    def run(self):
        try:
            self.logger.info(f"Начало конвертации: {self.input_file} -> {self.output_file}")
            
            success = self.processor.convert_file(
                self.input_file,
                self.output_file,
                **self.conversion_options,
                progress_callback=self.progress_updated.emit
            )
            
            if success:
                self.logger.info("Конвертация завершена успешно")
                self.processing_finished.emit(True, self.localization.get_text("conversion_complete_file").format(
                    filename=os.path.basename(self.output_file)
                ))
            else:
                self.error.emit(self.localization.get_text("conversion_failed"))
                
        except Exception as e:
            self.logger.error(f"Ошибка конвертации: {str(e)}")
            self.error.emit(str(e))


class ConversionTab(QWidget):
    """Вкладка для перекодировки файлов"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.processor = FFmpegProcessor()
        self.worker = None
        self.file_info = None
        
        # Инициализация локализации
        self.localization = get_localization()
        
        self.setup_ui()
        self.setup_connections()
        
        # Проверка доступности ffmpeg
        if not self.processor.is_available():
            self.show_ffmpeg_warning()
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Выбор исходного файла
        file_layout = QHBoxLayout()
        file_label = QLabel(self.localization.get_text("source_file_label"))
        file_label.setFixedWidth(120)
        file_label.setFixedHeight(30)
        
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText(self.localization.get_text("select_media_file_hint"))
        self.file_input.setFixedHeight(30)
        self.file_input.setReadOnly(True)
        
        self.browse_file_button = QPushButton(self.localization.get_text("browse_button"))
        self.browse_file_button.setFixedHeight(30)
        self.browse_file_button.setFixedWidth(100)
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.browse_file_button)
        
        layout.addLayout(file_layout)
        
        # Информация о файле
        self.file_info_label = QLabel(self.localization.get_text("no_file_selected"))
        self.file_info_label.setStyleSheet("color: #666; font-size: 11px;")
        self.file_info_label.setWordWrap(True)
        layout.addWidget(self.file_info_label)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Настройки конвертации
        conversion_group = QGroupBox(self.localization.get_text("conversion_settings"))
        conversion_layout = QVBoxLayout(conversion_group)
        
        # Кнопка справки с улучшенным дизайном в правом углу заголовка
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(32, 32)
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 16px;
                font-weight: bold;
                font-size: 16px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.help_button.setToolTip("Справка по параметрам конвертации")
        
        # Добавляем кнопку справки в правый угол заголовка группы
        conversion_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # Создаем layout для размещения кнопки справки в правом углу
        help_layout = QHBoxLayout()
        help_layout.addStretch()
        help_layout.addWidget(self.help_button)
        help_layout.setContentsMargins(0, 0, 10, 0)
        conversion_layout.addLayout(help_layout)
        
        # Формат вывода
        format_layout = QHBoxLayout()
        format_label = QLabel(self.localization.get_text("output_format_label"))
        format_label.setFixedWidth(120)
        
        self.format_combo = QComboBox()
        self.format_combo.setFixedHeight(30)
        # Добавляем форматы с соответствующими данными
        formats = [
            ("MP4", "mp4"), ("AVI", "avi"), ("MKV", "mkv"), ("MOV", "mov"), 
            ("WMV", "wmv"), ("FLV", "flv"), ("WEBM", "webm"),
            ("MP3", "mp3"), ("AAC", "aac"), ("FLAC", "flac"), 
            ("WAV", "wav"), ("OGG", "ogg"), ("M4A", "m4a")
        ]
        for display_name, format_code in formats:
            self.format_combo.addItem(display_name, format_code)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        
        conversion_layout.addLayout(format_layout)
        
        # Видео кодек
        self.video_codec_layout = QHBoxLayout()
        video_codec_label = QLabel(self.localization.get_text("video_codec_label"))
        video_codec_label.setFixedWidth(120)
        
        self.video_codec_combo = QComboBox()
        self.video_codec_combo.setFixedHeight(30)
        # Инициализируем с правильными кодеками для MP4 по умолчанию
        self.video_codec_combo.addItem(self.localization.get_text("copy_original"), "copy")
        self.video_codec_combo.addItem("H.264 (x264)", "libx264")
        self.video_codec_combo.addItem("H.265 (x265)", "libx265")
        
        self.video_codec_layout.addWidget(video_codec_label)
        self.video_codec_layout.addWidget(self.video_codec_combo)
        self.video_codec_layout.addStretch()
        
        conversion_layout.addLayout(self.video_codec_layout)
        
        # Аудио кодек
        audio_codec_layout = QHBoxLayout()
        audio_codec_label = QLabel(self.localization.get_text("audio_codec_label"))
        audio_codec_label.setFixedWidth(120)
        
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.setFixedHeight(30)
        self.audio_codec_combo.addItem(self.localization.get_text("copy_original"), "copy")
        # Добавляем аудио кодеки с соответствующими данными
        audio_codecs = [
            ("AAC", "aac"), ("MP3", "libmp3lame"), ("FLAC", "flac"), 
            ("Vorbis", "libvorbis"), ("Opus", "libopus")
        ]
        for display_name, codec_code in audio_codecs:
            self.audio_codec_combo.addItem(display_name, codec_code)
        
        audio_codec_layout.addWidget(audio_codec_label)
        audio_codec_layout.addWidget(self.audio_codec_combo)
        audio_codec_layout.addStretch()
        
        conversion_layout.addLayout(audio_codec_layout)
        
        layout.addWidget(conversion_group)
        
        # Настройки качества
        quality_group = QGroupBox(self.localization.get_text("quality_settings"))
        quality_layout = QVBoxLayout(quality_group)
        
        # Разрешение
        self.resolution_layout = QHBoxLayout()
        resolution_label = QLabel(self.localization.get_text("resolution_label"))
        resolution_label.setFixedWidth(120)
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem(self.localization.get_text("keep_original"), "original")
        # Добавляем разрешения с соответствующими данными
        resolutions = [
            ("3840x2160 (4K)", "3840x2160"), ("2560x1440 (1440p)", "2560x1440"), 
            ("1920x1080 (1080p)", "1920x1080"), ("1280x720 (720p)", "1280x720"),
            ("854x480 (480p)", "854x480"), ("640x360 (360p)", "640x360")
        ]
        for display_name, resolution_code in resolutions:
            self.resolution_combo.addItem(display_name, resolution_code)
        self.resolution_combo.setFixedHeight(30)
        
        self.resolution_layout.addWidget(resolution_label)
        self.resolution_layout.addWidget(self.resolution_combo)
        self.resolution_layout.addStretch()
        
        quality_layout.addLayout(self.resolution_layout)
        
        # Битрейт видео
        self.video_bitrate_layout = QHBoxLayout()
        video_bitrate_label = QLabel(self.localization.get_text("video_bitrate_label"))
        video_bitrate_label.setFixedWidth(120)
        
        self.video_bitrate_combo = QComboBox()
        self.video_bitrate_combo.addItem(self.localization.get_text("auto"), "auto")
        # Добавляем битрейты видео с соответствующими данными
        video_bitrates = [
            ("500k", "500k"), ("1000k", "1000k"), ("2000k", "2000k"), 
            ("4000k", "4000k"), ("8000k", "8000k"), ("15000k", "15000k"), ("25000k", "25000k")
        ]
        for display_name, bitrate_code in video_bitrates:
            self.video_bitrate_combo.addItem(display_name, bitrate_code)
        self.video_bitrate_combo.setFixedHeight(30)
        
        self.video_bitrate_layout.addWidget(video_bitrate_label)
        self.video_bitrate_layout.addWidget(self.video_bitrate_combo)
        self.video_bitrate_layout.addStretch()
        
        quality_layout.addLayout(self.video_bitrate_layout)
        
        # Битрейт аудио
        audio_bitrate_layout = QHBoxLayout()
        audio_bitrate_label = QLabel(self.localization.get_text("audio_bitrate_label"))
        audio_bitrate_label.setFixedWidth(120)
        
        self.audio_bitrate_combo = QComboBox()
        # Добавляем битрейты аудио с соответствующими данными
        audio_bitrates = [
            ("64k", "64k"), ("96k", "96k"), ("128k", "128k"), 
            ("192k", "192k"), ("256k", "256k"), ("320k", "320k")
        ]
        for display_name, bitrate_code in audio_bitrates:
            self.audio_bitrate_combo.addItem(display_name, bitrate_code)
        self.audio_bitrate_combo.setCurrentText("192k")
        self.audio_bitrate_combo.setFixedHeight(30)
        
        audio_bitrate_layout.addWidget(audio_bitrate_label)
        audio_bitrate_layout.addWidget(self.audio_bitrate_combo)
        audio_bitrate_layout.addStretch()
        
        quality_layout.addLayout(audio_bitrate_layout)
        
        layout.addWidget(quality_group)
        
        # Путь сохранения
        save_layout = QHBoxLayout()
        save_label = QLabel(self.localization.get_text("save_path_label"))
        save_label.setFixedWidth(120)
        save_label.setFixedHeight(30)
        
        self.save_input = QLineEdit()
        self.save_input.setFixedHeight(30)
        self.save_input.setReadOnly(True)
        
        self.browse_save_button = QPushButton(self.localization.get_text("browse_button"))
        self.browse_save_button.setFixedHeight(30)
        self.browse_save_button.setFixedWidth(100)
        
        save_layout.addWidget(save_label)
        save_layout.addWidget(self.save_input)
        save_layout.addWidget(self.browse_save_button)
        
        layout.addLayout(save_layout)
        
        # Кнопка конвертации
        self.convert_button = QPushButton(self.localization.get_text("start_conversion"))
        self.convert_button.setFixedHeight(40)
        self.convert_button.setEnabled(False)
        layout.addWidget(self.convert_button)
        
        layout.addStretch()
        
        # Установка пути сохранения по умолчанию
        default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "downloads")
        self.save_input.setText(default_path)
        
    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        try:
            # Проверяем существование элементов перед подключением сигналов
            if hasattr(self, 'browse_file_button') and self.browse_file_button:
                self.browse_file_button.clicked.connect(self.browse_source_file)
            
            if hasattr(self, 'browse_save_button') and self.browse_save_button:
                self.browse_save_button.clicked.connect(self.browse_save_directory)
            
            if hasattr(self, 'convert_button') and self.convert_button:
                self.convert_button.clicked.connect(self.start_conversion)
            
            # Изменение формата
            if hasattr(self, 'format_combo') and self.format_combo:
                self.format_combo.currentTextChanged.connect(self.on_format_changed)
            
            # Кнопка справки
            if hasattr(self, 'help_button') and self.help_button:
                self.help_button.clicked.connect(self.show_help_dialog)
                
        except Exception as e:
            self.logger.error(f"Ошибка при настройке соединений: {str(e)}")
    
    def browse_source_file(self):
        """Выбор исходного файла"""
        try:
            file_path, filter_used = QFileDialog.getOpenFileName(
                self,
                self.localization.get_text("select_media_file"),
                "",
                self.localization.get_text("media_files_filter")
            )
            
            if file_path:
                # Проверяем существование файла
                if not os.path.exists(file_path):
                    QMessageBox.warning(
                        self, 
                        self.localization.get_text("warning"), 
                        self.localization.get_text("file_not_found")
                    )
                    return
                
                # Проверяем доступность файла для чтения
                if not os.access(file_path, os.R_OK):
                    QMessageBox.warning(
                        self, 
                        self.localization.get_text("warning"), 
                        self.localization.get_text("file_not_readable")
                    )
                    return
                
                self.file_input.setText(file_path)
                self.update_file_info(file_path)
                self.update_output_filename()
                self.convert_button.setEnabled(True)
                
        except Exception as e:
            self.logger.error(f"Ошибка при выборе файла: {str(e)}")
            QMessageBox.critical(
                self, 
                self.localization.get_text("error"), 
                f"Ошибка при выборе файла: {str(e)}"
            )
    
    def browse_save_directory(self):
        """Выбор папки для сохранения"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self,
                self.localization.get_text("select_save_directory"),
                ""
            )
            
            if directory:
                # Проверяем существование директории
                if not os.path.exists(directory):
                    QMessageBox.warning(
                        self, 
                        self.localization.get_text("warning"), 
                        self.localization.get_text("directory_not_found")
                    )
                    return
                
                # Проверяем доступность директории для записи
                if not os.access(directory, os.W_OK):
                    QMessageBox.warning(
                        self, 
                        self.localization.get_text("warning"), 
                        self.localization.get_text("directory_not_writable")
                    )
                    return
                
                self.save_input.setText(directory)
                self.update_output_filename()
                
        except Exception as e:
            self.logger.error(f"Ошибка при выборе директории: {str(e)}")
            QMessageBox.critical(
                self, 
                self.localization.get_text("error"), 
                f"Ошибка при выборе директории: {str(e)}"
            )
    
    def update_file_info(self, file_path: str):
        """Обновление информации о файле"""
        try:
            if not file_path or not os.path.exists(file_path):
                self.file_info_label.setText(self.localization.get_text("no_file_selected"))
                return
                
            # Получаем базовую информацию о файле
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            filename = os.path.basename(file_path)
            
            # Проверяем размер файла (предупреждение для очень больших файлов)
            if file_size_mb > 1000:  # Больше 1 ГБ
                QMessageBox.information(
                    self,
                    self.localization.get_text("info"),
                    f"Выбран большой файл ({file_size_mb:.1f} МБ). Конвертация может занять много времени."
                )
            
            if self.processor.is_available():
                try:
                    self.file_info = self.processor.get_file_info(file_path)
                    
                    if self.file_info:
                        # Форматируем информацию
                        duration = self._format_duration(self.file_info.get('duration', 0))
                        size = self._format_size(self.file_info.get('size', file_size))
                        
                        info_lines = [f"Длительность: {duration} | Размер: {size}"]
                        
                        # Информация о видео
                        if self.file_info.get('video_streams'):
                            video = self.file_info['video_streams'][0]
                            video_info = f"Видео: {video.get('codec', 'N/A')}, {video.get('width', 0)}x{video.get('height', 0)}"
                            if video.get('bitrate'):
                                video_info += f", {self._format_bitrate(video['bitrate'])}"
                            info_lines.append(video_info)
                        
                        # Информация об аудио
                        if self.file_info.get('audio_streams'):
                            audio = self.file_info['audio_streams'][0]
                            audio_info = f"Аудио: {audio.get('codec', 'N/A')}, {audio.get('channels', 0)} каналов"
                            if audio.get('bitrate'):
                                audio_info += f", {self._format_bitrate(audio['bitrate'])}"
                            info_lines.append(audio_info)
                        
                        self.file_info_label.setText("\n".join(info_lines))
                    else:
                        self.file_info_label.setText(f"Файл: {filename}\n(не удалось получить информацию)")
                        
                except Exception as ffmpeg_error:
                    self.logger.warning(f"Ошибка анализа файла через ffmpeg: {str(ffmpeg_error)}")
                    self.file_info_label.setText(f"Файл: {filename}\n(ошибка анализа ffmpeg)")
            else:
                self.file_info_label.setText(f"Файл: {filename}\n(ffmpeg недоступен для анализа)")
                
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о файле: {str(e)}")
            try:
                filename = os.path.basename(file_path) if file_path else "неизвестный файл"
            except:
                filename = "неизвестный файл"
            self.file_info_label.setText(f"Файл: {filename}\n(ошибка анализа)")
    
    def on_format_changed(self):
        """Обработка изменения выходного формата"""
        format_type = self.format_combo.currentData()
        
        # Показываем/скрываем настройки видео в зависимости от формата
        is_video_format = format_type in ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm']
        
        # Управление видимостью элементов видео
        for i in range(self.video_codec_layout.count()):
            widget = self.video_codec_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(is_video_format)
        
        for i in range(self.resolution_layout.count()):
            widget = self.resolution_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(is_video_format)
        
        for i in range(self.video_bitrate_layout.count()):
            widget = self.video_bitrate_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(is_video_format)
        
        # Обновляем кодеки в зависимости от формата
        self.update_codec_options(format_type)
        self.update_output_filename()
    
    def update_codec_options(self, format_type: str):
        """Обновление опций кодеков в зависимости от формата"""
        # Очищаем и заполняем видеокодеки
        self.video_codec_combo.clear()
        if format_type in ['mp4', 'mkv', 'mov']:
            self.video_codec_combo.addItem(_("copy_original"), "copy")
            self.video_codec_combo.addItem("H.264 (x264)", "libx264")
            self.video_codec_combo.addItem("H.265 (x265)", "libx265")
            self.video_codec_combo.addItem("AV1", "libaom-av1")
        elif format_type == 'webm':
            self.video_codec_combo.addItem("VP9", "libvpx-vp9")
            self.video_codec_combo.addItem("VP8", "libvpx")
            self.video_codec_combo.addItem("AV1", "libaom-av1")
            self.video_codec_combo.addItem(_("copy_original"), "copy")
        elif format_type in ['avi', 'wmv', 'flv']:
            self.video_codec_combo.addItem(_("copy_original"), "copy")
            self.video_codec_combo.addItem("H.264 (x264)", "libx264")
        
        # Очищаем и заполняем аудиокодеки
        self.audio_codec_combo.clear()
        if format_type in ['mp4', 'mkv', 'mov', 'avi', 'wmv', 'flv']:
            self.audio_codec_combo.addItem("AAC", "aac")
            self.audio_codec_combo.addItem("MP3", "libmp3lame")
            self.audio_codec_combo.addItem(_("copy_original"), "copy")
        elif format_type == 'webm':
            self.audio_codec_combo.addItem("Opus", "libopus")
            self.audio_codec_combo.addItem("Vorbis", "libvorbis")
            self.audio_codec_combo.addItem(_("copy_original"), "copy")
        elif format_type == 'mp3':
            self.audio_codec_combo.addItem("MP3", "libmp3lame")
        elif format_type == 'aac':
            self.audio_codec_combo.addItem("AAC", "aac")
        elif format_type == 'flac':
            self.audio_codec_combo.addItem("FLAC", "flac")
        elif format_type == 'wav':
            self.audio_codec_combo.addItem("PCM", "pcm_s16le")
    
    def update_output_filename(self):
        """Обновление имени выходного файла"""
        try:
            if not self.file_input.text() or not self.save_input.text():
                return
            
            input_file = self.file_input.text()
            save_dir = self.save_input.text()
            
            # Проверяем существование исходного файла
            if not os.path.exists(input_file):
                self.logger.warning(f"Исходный файл не найден: {input_file}")
                return
            
            # Проверяем существование директории сохранения
            if not os.path.exists(save_dir):
                self.logger.warning(f"Директория сохранения не найдена: {save_dir}")
                return
            
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            format_type = self.format_combo.currentData()
            
            # Проверяем, что формат выбран
            if not format_type:
                self.logger.warning("Формат вывода не выбран")
                return
            
            # Создаем безопасное имя файла
            safe_base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_base_name:
                safe_base_name = "converted_file"
            
            output_file = os.path.join(save_dir, f"{safe_base_name}_converted.{format_type}")
            self.output_file = output_file
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении имени выходного файла: {str(e)}")
            self.output_file = None
    
    def start_conversion(self):
        """Запуск процесса конвертации"""
        try:
            # Проверяем наличие исходного файла
            input_file = self.file_input.text().strip()
            if not input_file:
                QMessageBox.warning(
                    self, 
                    self.localization.get_text("warning"), 
                    self.localization.get_text("select_input_file")
                )
                return
            
            if not os.path.exists(input_file):
                QMessageBox.warning(
                    self, 
                    self.localization.get_text("warning"), 
                    self.localization.get_text("input_file_not_found")
                )
                return
            
            # Проверяем доступность файла для чтения
            if not os.access(input_file, os.R_OK):
                QMessageBox.warning(
                    self, 
                    self.localization.get_text("warning"), 
                    self.localization.get_text("input_file_not_readable")
                )
                return
            
            # Проверяем директорию сохранения
            save_directory = self.save_input.text().strip()
            if not save_directory:
                QMessageBox.warning(
                    self, 
                    self.localization.get_text("warning"), 
                    self.localization.get_text("select_save_directory")
                )
                return
            
            if not os.path.exists(save_directory):
                QMessageBox.warning(
                    self, 
                    self.localization.get_text("warning"), 
                    self.localization.get_text("save_directory_not_found")
                )
                return
            
            if not os.access(save_directory, os.W_OK):
                QMessageBox.warning(
                    self, 
                    self.localization.get_text("warning"), 
                    self.localization.get_text("save_directory_not_writable")
                )
                return
            
            # Проверяем доступность ffmpeg
            if not self.processor.is_available():
                self.show_ffmpeg_warning()
                return
            
            self.update_output_filename()
            
            # Проверяем, не перезаписываем ли мы исходный файл
            if os.path.abspath(input_file) == os.path.abspath(self.output_file):
                QMessageBox.warning(
                    self, 
                    self.localization.get_text("warning"), 
                    "Выходной файл не может совпадать с исходным файлом"
                )
                return
            
            # Проверяем, существует ли выходной файл
            if os.path.exists(self.output_file):
                reply = QMessageBox.question(
                    self,
                    self.localization.get_text("confirm"),
                    f"Файл {os.path.basename(self.output_file)} уже существует. Перезаписать?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Собираем опции конвертации
            conversion_options = {}
            
            # Добавляем только поддерживаемые параметры
            if self.video_codec_combo.isVisible() and self.video_codec_combo.currentData():
                conversion_options['video_codec'] = self.video_codec_combo.currentData()
            
            if self.audio_codec_combo.currentData():
                conversion_options['audio_codec'] = self.audio_codec_combo.currentData()
            
            if self.video_bitrate_combo.isVisible() and self.video_bitrate_combo.currentData():
                conversion_options['video_bitrate'] = self.video_bitrate_combo.currentData()
            
            if self.audio_bitrate_combo.currentData():
                conversion_options['audio_bitrate'] = self.audio_bitrate_combo.currentData()
            
            if self.resolution_combo.isVisible() and self.resolution_combo.currentData():
                conversion_options['resolution'] = self.resolution_combo.currentData()
            
            # Создаем рабочий поток
            self.worker = ConversionWorker(
                input_file,
                self.output_file,
                conversion_options
            )
            
            # Подключаем сигналы
            self.worker.progress_updated.connect(self.on_progress_updated)
            self.worker.processing_finished.connect(self.on_processing_finished)
            self.worker.error.connect(self.on_processing_error)
            
            # Запускаем конвертацию
            self.worker.start()
            self.set_ui_enabled(False)
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске конвертации: {str(e)}")
            QMessageBox.critical(
                self, 
                self.localization.get_text("error"), 
                f"Ошибка при запуске конвертации: {str(e)}"
            )
    
    def on_progress_updated(self, progress: float, status: str):
        """Обработка обновления прогресса"""
        # Этот сигнал будет подключен к прогресс-бару в главном окне
        pass
    
    def on_processing_finished(self, success: bool, message: str):
        """Обработка завершения конвертации"""
        self.worker = None
        self.set_ui_enabled(True)
        
        if success:
            QMessageBox.information(self, self.localization.get_text("success"), message)
    
    def on_processing_error(self, error_message: str):
        """Обработка ошибки конвертации"""
        self.worker = None
        self.set_ui_enabled(True)
        QMessageBox.critical(self, self.localization.get_text("error"), error_message)
    
    def set_ui_enabled(self, enabled: bool):
        """Включение/отключение элементов интерфейса"""
        try:
            # Проверяем существование элементов перед их использованием
            if hasattr(self, 'browse_file_button') and self.browse_file_button:
                self.browse_file_button.setEnabled(enabled)
            
            if hasattr(self, 'browse_save_button') and self.browse_save_button:
                self.browse_save_button.setEnabled(enabled)
            
            if hasattr(self, 'convert_button') and self.convert_button:
                file_selected = hasattr(self, 'file_input') and self.file_input and bool(self.file_input.text())
                self.convert_button.setEnabled(enabled and file_selected)
            
            # Проверяем комбобоксы
            combo_boxes = [
                'format_combo', 'video_codec_combo', 'audio_codec_combo',
                'resolution_combo', 'video_bitrate_combo', 'audio_bitrate_combo'
            ]
            
            for combo_name in combo_boxes:
                if hasattr(self, combo_name):
                    combo = getattr(self, combo_name)
                    if combo:
                        combo.setEnabled(enabled)
                        
        except Exception as e:
            self.logger.error(f"Ошибка при изменении состояния UI: {str(e)}")
    
    def show_ffmpeg_warning(self):
        """Показ предупреждения об отсутствии ffmpeg"""
        QMessageBox.warning(
            self,
            self.localization.get_text("ffmpeg_warning_title"),
            self.localization.get_text("ffmpeg_warning_message")
        )
    
    def _format_duration(self, seconds: float) -> str:
        """Форматирование длительности"""
        if seconds < 60:
            return f"{int(seconds)}с"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}м {secs}с"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}ч {minutes}м"
    
    def _format_size(self, bytes_size: int) -> str:
        """Форматирование размера файла"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} ТБ"
    
    def _format_bitrate(self, bitrate: int) -> str:
        """Форматирование битрейта"""
        if bitrate >= 1000000:
            return f"{bitrate / 1000000:.1f} Mbps"
        else:
            return f"{bitrate / 1000:.0f} kbps"
    
    def show_help_dialog(self):
        """Показ диалогового окна с справкой по параметрам конвертации"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Справка по параметрам конвертации")
        dialog.setModal(True)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Создаем область прокрутки
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Содержимое справки
        help_content = """
<h2>Справка по параметрам конвертации</h2>

<h3>📁 Формат вывода</h3>
<p><b>Что это:</b> Формат файла, в который будет конвертирован исходный файл.</p>
<p><b>Когда использовать:</b></p>
<ul>
<li><b>MP4</b> - универсальный формат, подходит для большинства устройств и платформ</li>
<li><b>AVI</b> - старый формат, хорошая совместимость со старыми программами</li>
<li><b>MKV</b> - поддерживает множество дорожек, субтитры, высокое качество</li>
<li><b>MOV</b> - формат Apple, лучше всего для устройств Mac/iOS</li>
<li><b>WEBM</b> - оптимизирован для веб-воспроизведения</li>
<li><b>MP3</b> - только аудио, универсальный формат для музыки</li>
<li><b>FLAC</b> - только аудио, без потерь качества</li>
</ul>

<h3>🎬 Видеокодек</h3>
<p><b>Что это:</b> Алгоритм сжатия видео.</p>
<p><b>Когда использовать:</b></p>
<ul>
<li><b>H.264 (libx264)</b> - лучший баланс качества и размера, универсальная совместимость</li>
<li><b>H.265 (libx265)</b> - лучшее сжатие, меньший размер файла, но требует больше ресурсов</li>
<li><b>VP9</b> - открытый стандарт, хорош для веб-контента</li>
<li><b>AV1</b> - новейший кодек, отличное сжатие, но медленная обработка</li>
</ul>

<h3>📐 Разрешение</h3>
<p><b>Что это:</b> Размер видео в пикселях (ширина × высота).</p>
<p><b>Когда использовать:</b></p>
<ul>
<li><b>Исходное</b> - сохранить оригинальное разрешение</li>
<li><b>1920×1080 (Full HD)</b> - стандарт для большинства экранов</li>
<li><b>1280×720 (HD)</b> - меньший размер файла, подходит для мобильных устройств</li>
<li><b>3840×2160 (4K)</b> - высокое качество для больших экранов</li>
</ul>

<h3>📊 Видео битрейт</h3>
<p><b>Что это:</b> Количество данных в секунду для видео. Выше = лучше качество, но больше размер файла.</p>
<p><b>Рекомендации:</b></p>
<ul>
<li><b>1-3 Mbps</b> - для мобильных устройств, низкое качество</li>
<li><b>5-10 Mbps</b> - хорошее качество для Full HD</li>
<li><b>15-25 Mbps</b> - высокое качество для Full HD</li>
<li><b>35-50 Mbps</b> - для 4K видео</li>
</ul>

<h3>🔊 Аудио битрейт</h3>
<p><b>Что это:</b> Качество звука. Выше = лучше звук, но больше размер файла.</p>
<p><b>Рекомендации:</b></p>
<ul>
<li><b>128 kbps</b> - приемлемое качество для речи</li>
<li><b>192 kbps</b> - хорошее качество для музыки</li>
<li><b>320 kbps</b> - высокое качество, близко к CD</li>
</ul>

<h3>💡 Общие советы</h3>
<ul>
<li>Для YouTube: MP4 + H.264 + 1080p + 8-12 Mbps</li>
<li>Для мобильных: MP4 + H.264 + 720p + 3-5 Mbps</li>
<li>Для архивирования: MKV + H.265 + исходное разрешение</li>
<li>Для быстрой обработки: используйте аппаратное ускорение (если доступно)</li>
</ul>
        """
        
        # Создаем текстовое поле с HTML-содержимым
        text_edit = QTextEdit()
        text_edit.setHtml(help_content)
        text_edit.setReadOnly(True)
        
        scroll_layout.addWidget(text_edit)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(dialog.accept)
        close_button.setFixedHeight(30)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        dialog.exec()