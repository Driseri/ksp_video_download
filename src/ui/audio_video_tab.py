#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QRadioButton, QButtonGroup, 
    QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread

from src.core.ffmpeg_processor import FFmpegProcessor
from src.core.logger import get_logger
from src.core.localization import get_localization, _


class AudioVideoWorker(QThread):
    """Рабочий поток для обработки аудио/видео"""
    progress_updated = Signal(float, str)
    processing_finished = Signal(bool, str)
    error = Signal(str)
    
    def __init__(self, input_file: str, output_file: str, operation: str, 
                 format_type: str = 'mp3', quality: str = '192k'):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.operation = operation  # 'extract_audio' или 'extract_video'
        self.format_type = format_type
        self.quality = quality
        self.processor = FFmpegProcessor()
        self.logger = get_logger()
    
    def run(self):
        try:
            self.logger.info(f"Начало операции {self.operation}: {self.input_file}")
            
            # Валидация входных данных
            if not os.path.exists(self.input_file):
                raise FileNotFoundError(f"Входной файл не найден: {self.input_file}")
            
            if not os.path.isfile(self.input_file):
                raise ValueError(f"Указанный путь не является файлом: {self.input_file}")
            
            # Проверяем размер файла
            file_size = os.path.getsize(self.input_file)
            if file_size == 0:
                raise ValueError("Входной файл пуст")
            
            self.logger.info(f"Размер входного файла: {file_size} байт")
            
            # Проверяем доступность выходной директории
            output_dir = os.path.dirname(self.output_file)
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.logger.info(f"Создана выходная директория: {output_dir}")
                except OSError as e:
                    raise RuntimeError(f"Не удалось создать выходную директорию: {e}")
            
            # Проверяем права на запись
            if not os.access(output_dir, os.W_OK):
                raise PermissionError(f"Нет прав на запись в директорию: {output_dir}")
            
            if self.operation == 'extract_audio':
                success = self.processor.extract_audio(
                    self.input_file, 
                    self.output_file,
                    self.format_type,
                    self.quality,
                    progress_callback=self.progress_updated.emit
                )
            elif self.operation == 'extract_video':
                success = self.processor.extract_video(
                    self.input_file,
                    self.output_file,
                    progress_callback=self.progress_updated.emit
                )
            else:
                raise ValueError(f"Неизвестная операция: {self.operation}")
            
            if success:
                # Дополнительная проверка результата
                if not os.path.exists(self.output_file):
                    raise RuntimeError("Выходной файл не был создан")
                
                output_size = os.path.getsize(self.output_file)
                if output_size == 0:
                    raise RuntimeError("Выходной файл пуст")
                
                self.logger.info(f"Операция {self.operation} завершена успешно. Размер выходного файла: {output_size} байт")
                self.processing_finished.emit(True, _("processing_complete_file").format(
                    filename=os.path.basename(self.output_file)
                ))
            else:
                self.error.emit(_("processing_failed"))
                
        except FileNotFoundError as e:
            self.logger.error(f"Файл не найден: {str(e)}")
            self.error.emit(_("file_not_found").format(file=str(e)))
        except PermissionError as e:
            self.logger.error(f"Ошибка доступа: {str(e)}")
            self.error.emit(f"Ошибка доступа: {str(e)}")
        except ValueError as e:
            self.logger.error(f"Ошибка валидации: {str(e)}")
            self.error.emit(f"Ошибка валидации: {str(e)}")
        except Exception as e:
            self.logger.error(f"Ошибка операции {self.operation}: {str(e)}")
            self.error.emit(str(e))


class AudioVideoTab(QWidget):
    """Вкладка для разделения аудио и видео"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.processor = FFmpegProcessor()
        self.worker = None
        
        # Инициализация локализации
        get_localization()
        
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
        file_label = QLabel(_("source_file_label"))
        file_label.setFixedWidth(120)
        file_label.setFixedHeight(30)
        
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText(_("select_video_file_hint"))
        self.file_input.setFixedHeight(30)
        self.file_input.setReadOnly(True)
        
        self.browse_file_button = QPushButton(_("browse_button"))
        self.browse_file_button.setFixedHeight(30)
        self.browse_file_button.setFixedWidth(100)
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.browse_file_button)
        layout.addLayout(file_layout)
        
        # Информация о файле
        self.file_info_frame = QFrame()
        self.file_info_frame.setFrameShape(QFrame.StyledPanel)
        self.file_info_frame.setFixedHeight(60)
        self.file_info_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f9f9f9;
                padding: 5px;
            }
        """)
        
        info_layout = QVBoxLayout(self.file_info_frame)
        info_layout.setContentsMargins(10, 5, 10, 5)
        
        self.file_info_label = QLabel(_("no_file_selected"))
        self.file_info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(self.file_info_label)
        
        layout.addWidget(self.file_info_frame)
        
        # Выбор операции
        operation_layout = QVBoxLayout()
        operation_label = QLabel(_("operation_label"))
        operation_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        operation_layout.addWidget(operation_label)
        
        self.operation_group = QButtonGroup()
        
        self.extract_audio_radio = QRadioButton(_("extract_audio_only"))
        self.extract_audio_radio.setChecked(True)
        self.operation_group.addButton(self.extract_audio_radio, 0)
        
        self.extract_video_radio = QRadioButton(_("extract_video_only"))
        self.operation_group.addButton(self.extract_video_radio, 1)
        
        operation_layout.addWidget(self.extract_audio_radio)
        operation_layout.addWidget(self.extract_video_radio)
        layout.addLayout(operation_layout)
        
        # Настройки аудио (показываются только при извлечении аудио)
        self.audio_settings_frame = QFrame()
        audio_settings_layout = QVBoxLayout(self.audio_settings_frame)
        audio_settings_layout.setContentsMargins(0, 10, 0, 0)
        
        # Формат аудио
        audio_format_layout = QHBoxLayout()
        audio_format_label = QLabel(_("audio_format_label"))
        audio_format_label.setFixedWidth(120)
        audio_format_label.setFixedHeight(30)
        
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItem("MP3", "mp3")
        self.audio_format_combo.addItem("AAC", "aac")
        self.audio_format_combo.addItem("FLAC", "flac")
        self.audio_format_combo.addItem("WAV", "wav")
        self.audio_format_combo.setFixedHeight(30)
        
        # Кнопка помощи для формата
        self.format_help_button = QPushButton("?")
        self.format_help_button.setFixedSize(25, 25)
        self.format_help_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 12px;
                background-color: #f0f0f0;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.format_help_button.setToolTip("Нажмите для получения справки по форматам аудио")
        
        audio_format_layout.addWidget(audio_format_label)
        audio_format_layout.addWidget(self.audio_format_combo)
        audio_format_layout.addWidget(self.format_help_button)
        audio_format_layout.addStretch()
        audio_settings_layout.addLayout(audio_format_layout)
        
        # Качество аудио
        audio_quality_layout = QHBoxLayout()
        audio_quality_label = QLabel(_("audio_quality_label"))
        audio_quality_label.setFixedWidth(120)
        audio_quality_label.setFixedHeight(30)
        
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItem("320 kbps", "320k")
        self.audio_quality_combo.addItem("256 kbps", "256k")
        self.audio_quality_combo.addItem("192 kbps", "192k")
        self.audio_quality_combo.addItem("128 kbps", "128k")
        self.audio_quality_combo.addItem("96 kbps", "96k")
        self.audio_quality_combo.setCurrentText("192 kbps")
        self.audio_quality_combo.setFixedHeight(30)
        
        # Кнопка помощи для качества
        self.quality_help_button = QPushButton("?")
        self.quality_help_button.setFixedSize(25, 25)
        self.quality_help_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 12px;
                background-color: #f0f0f0;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.quality_help_button.setToolTip("Нажмите для получения справки по качеству аудио")
        
        audio_quality_layout.addWidget(audio_quality_label)
        audio_quality_layout.addWidget(self.audio_quality_combo)
        audio_quality_layout.addWidget(self.quality_help_button)
        audio_quality_layout.addStretch()
        audio_settings_layout.addLayout(audio_quality_layout)
        
        layout.addWidget(self.audio_settings_frame)
        
        # Путь сохранения
        save_layout = QHBoxLayout()
        save_label = QLabel(_("save_path_label"))
        save_label.setFixedWidth(120)
        save_label.setFixedHeight(30)
        
        self.save_path_input = QLineEdit()
        self.save_path_input.setFixedHeight(30)
        self.save_path_input.setReadOnly(True)
        
        self.browse_save_button = QPushButton(_("browse_button"))
        self.browse_save_button.setFixedHeight(30)
        self.browse_save_button.setFixedWidth(100)
        
        save_layout.addWidget(save_label)
        save_layout.addWidget(self.save_path_input)
        save_layout.addWidget(self.browse_save_button)
        layout.addLayout(save_layout)
        
        # Растягивающийся пробел
        layout.addStretch()
        
        # Кнопка обработки
        process_layout = QHBoxLayout()
        process_layout.addStretch()
        
        self.process_button = QPushButton(_("start_processing"))
        self.process_button.setStyleSheet("""
            QPushButton {
                font-size: 14px; 
                font-weight: bold;
                padding: 10px 20px; 
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.process_button.setFixedHeight(40)
        self.process_button.setFixedWidth(160)
        self.process_button.setEnabled(False)
        
        process_layout.addWidget(self.process_button)
        process_layout.addStretch()
        layout.addLayout(process_layout)
        
        # Установка пути сохранения по умолчанию
        default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "downloads")
        self.save_path_input.setText(default_path)
    
    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        self.browse_file_button.clicked.connect(self.browse_source_file)
        self.browse_save_button.clicked.connect(self.browse_save_path)
        self.process_button.clicked.connect(self.start_processing)
        
        # Переключение между операциями
        self.operation_group.buttonClicked.connect(self.on_operation_changed)
        
        # Изменение формата аудио
        self.audio_format_combo.currentTextChanged.connect(self.update_quality_options)
        
        # Кнопки помощи
        self.format_help_button.clicked.connect(self.show_format_help)
        self.quality_help_button.clicked.connect(self.show_quality_help)
    
    def browse_source_file(self):
        """Выбор исходного файла"""
        file_path, filter_used = QFileDialog.getOpenFileName(
            self,
            _("select_video_file"),
            "",
            _("video_files_filter")
        )
        
        if file_path:
            self.file_input.setText(file_path)
            self.update_file_info(file_path)
            self.update_output_filename()
            self.process_button.setEnabled(True)
    
    def browse_save_path(self):
        """Выбор пути сохранения"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            _("select_save_directory"),
            self.save_path_input.text()
        )
        
        if dir_path:
            self.save_path_input.setText(dir_path)
            self.update_output_filename()
    
    def update_file_info(self, file_path: str):
        """Обновление информации о файле"""
        try:
            if self.processor.is_available():
                info = self.processor.get_file_info(file_path)
                
                # Форматируем информацию
                duration = self._format_duration(info.get('duration', 0))
                size = self._format_size(info.get('size', 0))
                
                video_info = ""
                if info.get('video_streams'):
                    video = info['video_streams'][0]
                    video_info = f"{video.get('codec', 'N/A')}, {video.get('width', 0)}x{video.get('height', 0)}"
                
                audio_info = ""
                if info.get('audio_streams'):
                    audio = info['audio_streams'][0]
                    audio_info = f"{audio.get('codec', 'N/A')}, {audio.get('channels', 0)} каналов"
                
                info_text = f"Длительность: {duration} | Размер: {size}"
                if video_info:
                    info_text += f" | Видео: {video_info}"
                if audio_info:
                    info_text += f" | Аудио: {audio_info}"
                
                self.file_info_label.setText(info_text)
            else:
                filename = os.path.basename(file_path)
                self.file_info_label.setText(f"Файл: {filename} (ffmpeg недоступен для анализа)")
                
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о файле: {str(e)}")
            filename = os.path.basename(file_path)
            self.file_info_label.setText(f"Файл: {filename} (ошибка анализа)")
    
    def on_operation_changed(self):
        """Обработка изменения типа операции"""
        is_audio = self.extract_audio_radio.isChecked()
        self.audio_settings_frame.setVisible(is_audio)
        self.update_output_filename()
    
    def update_quality_options(self):
        """Обновление опций качества в зависимости от формата"""
        format_type = self.audio_format_combo.currentData()
        
        self.audio_quality_combo.clear()
        
        if format_type in ['mp3', 'aac']:
            self.audio_quality_combo.addItem("320 kbps", "320k")
            self.audio_quality_combo.addItem("256 kbps", "256k")
            self.audio_quality_combo.addItem("192 kbps", "192k")
            self.audio_quality_combo.addItem("128 kbps", "128k")
            self.audio_quality_combo.addItem("96 kbps", "96k")
            self.audio_quality_combo.setCurrentText("192 kbps")
        elif format_type == 'flac':
            self.audio_quality_combo.addItem(_("lossless"), "lossless")
        elif format_type == 'wav':
            self.audio_quality_combo.addItem(_("uncompressed"), "uncompressed")
        
        self.update_output_filename()
    
    def update_output_filename(self):
        """Обновление имени выходного файла"""
        if not self.file_input.text() or not self.save_path_input.text():
            return
        
        input_file = self.file_input.text()
        save_dir = self.save_path_input.text()
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        
        if self.extract_audio_radio.isChecked():
            format_type = self.audio_format_combo.currentData()
            output_file = os.path.join(save_dir, f"{base_name}_audio.{format_type}")
        else:
            # Для видео сохраняем исходное расширение
            original_ext = os.path.splitext(input_file)[1]
            output_file = os.path.join(save_dir, f"{base_name}_video{original_ext}")
        
        self.output_file = output_file
    
    def start_processing(self):
        """Запуск обработки файла"""
        if not self.file_input.text():
            QMessageBox.warning(self, _("warning"), _("select_source_file_first"))
            return
        
        if not self.processor.is_available():
            QMessageBox.critical(self, _("error"), _("ffmpeg_not_available"))
            return
        
        try:
            self.update_output_filename()
            
            operation = 'extract_audio' if self.extract_audio_radio.isChecked() else 'extract_video'
            format_type = self.audio_format_combo.currentData() if operation == 'extract_audio' else 'mp4'
            quality = self.audio_quality_combo.currentData() if operation == 'extract_audio' else '192k'
            
            # Создаем рабочий поток
            self.worker = AudioVideoWorker(
                self.file_input.text(),
                self.output_file,
                operation,
                format_type,
                quality
            )
            
            # Подключаем сигналы
            self.worker.progress_updated.connect(self.on_progress_updated)
            self.worker.processing_finished.connect(self.on_processing_finished)
            self.worker.error.connect(self.on_processing_error)
            
            # Запускаем обработку
            self.worker.start()
            self.set_ui_enabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, _("error"), str(e))
    
    def on_progress_updated(self, progress: float, status: str):
        """Обработка обновления прогресса"""
        # Этот сигнал будет подключен к прогресс-бару в главном окне
        pass
    
    def on_processing_finished(self, success: bool, message: str):
        """Обработка завершения операции"""
        self.set_ui_enabled(True)
        if success:
            QMessageBox.information(self, _("success"), message)
        
    def on_processing_error(self, error_message: str):
        """Обработка ошибки операции"""
        self.set_ui_enabled(True)
        QMessageBox.critical(self, _("error"), error_message)
    
    def set_ui_enabled(self, enabled: bool):
        """Включение/отключение элементов интерфейса"""
        self.browse_file_button.setEnabled(enabled)
        self.browse_save_button.setEnabled(enabled)
        self.process_button.setEnabled(enabled and bool(self.file_input.text()))
        self.audio_format_combo.setEnabled(enabled)
        self.audio_quality_combo.setEnabled(enabled)
        self.extract_audio_radio.setEnabled(enabled)
        self.extract_video_radio.setEnabled(enabled)
    
    def show_ffmpeg_warning(self):
        """Показ предупреждения об отсутствии ffmpeg"""
        QMessageBox.warning(
            self,
            _("ffmpeg_warning_title"),
            _("ffmpeg_warning_message")
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
    
    def show_format_help(self):
        """Показ справки по форматам аудио"""
        help_text = """
<b>Форматы аудио:</b><br><br>

<b>MP3</b> - Самый популярный формат<br>
• Хорошее сжатие и качество<br>
• Поддерживается всеми устройствами<br>
• Рекомендуется для общего использования<br><br>

<b>AAC</b> - Современный формат<br>
• Лучшее качество при том же размере, чем MP3<br>
• Используется в iTunes и YouTube<br>
• Хорошо подходит для мобильных устройств<br><br>

<b>FLAC</b> - Без потерь качества<br>
• Сохраняет оригинальное качество<br>
• Большой размер файлов<br>
• Для аудиофилов и архивирования<br><br>

<b>WAV</b> - Несжатый формат<br>
• Максимальное качество<br>
• Очень большие файлы<br>
• Для профессиональной работы
        """
        
        QMessageBox.information(self, "Справка по форматам", help_text)
    
    def show_quality_help(self):
        """Показ справки по качеству аудио"""
        help_text = """
<b>Качество аудио (битрейт):</b><br><br>

<b>96 kbps</b> - Низкое качество<br>
• Для речи и подкастов<br>
• Минимальный размер файла<br><br>

<b>128 kbps</b> - Приемлемое качество<br>
• Для фоновой музыки<br>
• Экономия места<br><br>

<b>192 kbps</b> - Хорошее качество (рекомендуется)<br>
• Оптимальный баланс качества и размера<br>
• Подходит для большинства случаев<br><br>

<b>256 kbps</b> - Высокое качество<br>
• Для качественного прослушивания<br>
• Заметно больший размер<br><br>

<b>320 kbps</b> - Максимальное качество<br>
 • Практически неотличимо от CD<br>
 • Самые большие файлы
        """
        
        QMessageBox.information(self, "Справка по качеству", help_text)