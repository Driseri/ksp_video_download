#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QComboBox, 
    QProgressBar, QFileDialog, QMessageBox, QStatusBar,
    QTabWidget, QRadioButton, QButtonGroup, QFrame, QApplication, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QThread, QMimeData, QProcess, QPropertyAnimation, QEasingCurve, QRect, Property, QTimer
from PySide6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent, QPainter, QColor, QPen, QMovie

import json
import re
from urllib.parse import urlparse
import yt_dlp

# Код для перезапуска приложения
RESTART_CODE = 1000

from src.core.downloader import VideoDownloader
from src.core.logger import get_logger
from src.core.localization import get_localization, _
from src.core.thread_manager import thread_manager
from src.core.base_worker import BaseWorker
from src.ui.audio_video_tab import AudioVideoTab
from src.ui.conversion_tab import ConversionTab


class DownloadWorker(BaseWorker):
    """Рабочий поток для загрузки видео"""
    download_finished = Signal(bool, str)
    
    def __init__(self, url, output_path, format_id, referrer=None):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.format_id = format_id
        self.referrer = referrer
        self.downloader = VideoDownloader()
        self._download_started = False
        self._ydl_instance = None  # Для отслеживания экземпляра yt-dlp
    
    def work(self):
        """Основная логика загрузки видео"""
        try:
            if self.check_cancelled():
                return
                
            # Валидация параметров перед началом загрузки
            if not self.url or not self.url.strip():
                self.error.emit("URL не может быть пустым")
                return
                
            if not self.output_path or not self.output_path.strip():
                self.error.emit("Путь для сохранения не может быть пустым")
                return
            
            self.logger.info(f"Начало загрузки видео: {self.url}")
            self.logger.info(f"ID формата: {self.format_id}, путь сохранения: {self.output_path}")
            
            if self.check_cancelled():
                return
                
            self._download_started = True
            
            # Используем ID формата напрямую
            ydl_opts = {
                'format': self.format_id,
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
            }
            
            # Добавляем referrer, если он указан
            if self.referrer:
                ydl_opts['http_headers'] = {
                    'Referer': self.referrer,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            
            # Добавляем хук прогресса
            ydl_opts['progress_hooks'] = [self.downloader._progress_hook(self._progress_callback)]
            
            # Загружаем видео напрямую через yt-dlp
            try:
                self._ydl_instance = yt_dlp.YoutubeDL(ydl_opts)
                # Регистрируем yt-dlp экземпляр для автоматической очистки
                self.add_resource_for_cleanup(self._ydl_instance, self._cleanup_ydl)
                
                with self._ydl_instance as ydl:
                    info = ydl.extract_info(self.url, download=True)
                    if info:
                        filename = ydl.prepare_filename(info)
                        if 'ext' in info and not filename.endswith(info['ext']):
                            base_filename = os.path.splitext(filename)[0]
                            filename = f"{base_filename}.{info['ext']}"
                        
                        result_file = os.path.join(self.output_path, os.path.basename(filename))
                    else:
                        raise Exception("Не удалось получить информацию о видео")
            except Exception as e:
                self.error.emit(f"Ошибка при загрузке видео: {str(e)}")
                return
            
            if self.check_cancelled():
                self.logger.info("Загрузка была отменена")
                return
            
            if result_file and os.path.exists(result_file):
                self.logger.info(f"Загрузка завершена успешно: {result_file}")
                self.download_finished.emit(True, f"Загрузка завершена: {os.path.basename(result_file)}")
            else:
                self.error.emit("Файл не был создан после загрузки")
                
        except ValueError as e:
            self.handle_error(e, f"Ошибка валидации: {str(e)}")
        except PermissionError as e:
            self.handle_error(e, f"Ошибка доступа: {str(e)}")
        except Exception as e:
            if not self.is_cancelled():
                self.handle_error(e, f"Ошибка загрузки: {str(e)}")
        finally:
            self._download_started = False
    
    def _cleanup_ydl(self):
        """Очистка ресурсов yt-dlp"""
        if self._ydl_instance:
            try:
                # Принудительно останавливаем все активные загрузки
                if hasattr(self._ydl_instance, '_download_retcode'):
                    self._ydl_instance._download_retcode = 1
                self.logger.debug("Ресурсы yt-dlp очищены")
            except Exception as e:
                self.logger.warning(f"Ошибка при очистке yt-dlp: {e}")
            finally:
                self._ydl_instance = None
    
    def terminate(self):
        """Переопределяем terminate для корректной остановки загрузки"""
        self.logger.info("Принудительное завершение загрузки")
        self._is_cancelled = True
        
        # Останавливаем yt-dlp если он активен
        if self._ydl_instance:
            try:
                if hasattr(self._ydl_instance, '_download_retcode'):
                    self._ydl_instance._download_retcode = 1
            except Exception as e:
                self.logger.warning(f"Ошибка при остановке yt-dlp: {e}")
        
        super().terminate()
    
    def _progress_callback(self, progress: float, status: str):
        """Обратный вызов для обновления прогресса с проверкой отмены"""
        if not self.is_cancelled():
            self.progress_updated.emit(progress, status)
    
    def cancel(self):
        """Отменяет загрузку"""
        super().cancel()
        if self._download_started:
            self.logger.info("Отмена загрузки по запросу пользователя")


class VideoInfoWorker(BaseWorker):
    """Рабочий поток для получения информации о видео"""
    info_fetched = Signal(dict)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.downloader = VideoDownloader()
        # Импортируем обработчик yt-dlp
        from src.core.yt_dlp_handler import YtDlpHandler
        self.yt_handler = YtDlpHandler()
        # Регистрируем yt_handler для очистки
        self.add_resource_for_cleanup(self.yt_handler, self._cleanup_yt_handler)
    
    def work(self):
        """Основная логика получения информации о видео"""
        try:
            if self.check_cancelled():
                return
                
            if not self.url or not self.url.strip():
                self.error.emit("URL не может быть пустым")
                return
            
            # Получаем информацию о видео через существующий метод
            video_info = self.yt_handler.get_video_info(self.url)
            
            if self.check_cancelled():
                return
            
            if video_info:
                # Выводим в консоль информацию для отладки
                self.logger.info(f"Получена информация о видео: {video_info.get('title', 'неизвестно')}")
                
                # Отправляем сигнал с информацией о видео
                self.info_fetched.emit(video_info)
            else:
                self.error.emit("Не удалось получить информацию о видео")
                    
        except Exception as e:
            # Обрабатываем все ошибки через базовый метод
            self.handle_error(e, f"Ошибка при получении информации о видео: {str(e)}")
    
    def _cleanup_yt_handler(self):
        """Очистка ресурсов YtDlpHandler"""
        if self.yt_handler:
            try:
                # Если у обработчика есть метод cleanup, вызываем его
                if hasattr(self.yt_handler, 'cleanup'):
                    self.yt_handler.cleanup()
                self.logger.debug("Ресурсы YtDlpHandler очищены")
            except Exception as e:
                self.logger.warning(f"Ошибка при очистке YtDlpHandler: {e}")
            finally:
                self.yt_handler = None


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def format_filesize(self, size_bytes):
        """Форматирует размер файла в человекочитаемый вид"""
        if not size_bytes:
            return "Неизвестно"
            
        # Конвертируем байты в более читаемый формат
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} ПБ"
    
    def __init__(self):
        super().__init__()
        
        # Инициализация локализации перед использованием
        get_localization()
        
        self.logger = get_logger()
        self.logger.info("Инициализация главного окна приложения")
        
        # Переменные для управления состоянием
        self.video_info_worker = None
        self.video_info_fetched = False
        self.current_video_info = None
        self.formats_data = {}  # Инициализация словаря форматов
        
        # Инициализация анимации загрузки
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_dots = 0
        self.original_button_text = "Получить данные о видео"
        
        self.setWindowTitle(_("app_title"))
        self.setMinimumSize(QSize(600, 460))  # Увеличена высота на 15% (400 -> 460)
        self.resize(1000, 700)
        
        # Загружаем иконку
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setup_ui()
        self.setup_connections()
        self.logger.info("Главное окно успешно инициализировано")
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной макет
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Заголовок приложения и переключатель языка
        header_layout = QHBoxLayout()
        
        # Заголовок приложения
        title_label = QLabel(_("app_title"))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        header_layout.addWidget(title_label, 1)
        
        # Переключатель языка
        lang_layout = QHBoxLayout()
        lang_label = QLabel(_("language_switch"))
        self.lang_toggle = LanguageToggle()
        
        # Получаем доступные языки
        localization = get_localization()
        
        # Устанавливаем текущий язык в toggle
        self.lang_toggle.set_language(localization.current_lang)
        
        # language_switch label скрыт по требованию
        lang_layout.addWidget(self.lang_toggle)
        header_layout.addLayout(lang_layout)
        
        main_layout.addLayout(header_layout)
        
        # Создаем вкладки
        self.tab_widget = QTabWidget()
        
        # Вкладка "Общие"
        self.general_tab = QWidget()
        self.setup_general_tab()
        self.tab_widget.addTab(self.general_tab, _("general_tab"))
        
        # Вкладка "Kinescope"
        self.kinescope_tab = QWidget()
        self.setup_kinescope_tab()
        self.tab_widget.addTab(self.kinescope_tab, _("kinescope_tab"))
        
        # Вкладка "Разделение аудио/видео"
        self.audio_video_tab = AudioVideoTab()
        self.tab_widget.addTab(self.audio_video_tab, _("audio_video_tab"))
        
        # Вкладка "Перекодировка файлов"
        self.conversion_tab = ConversionTab()
        self.tab_widget.addTab(self.conversion_tab, _("conversion_tab"))
        
        main_layout.addWidget(self.tab_widget)
        
        # Растягивающийся пробел
        main_layout.addStretch()
        
        # Статусная строка
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(_("status_ready"))
        
        # Установка пути сохранения по умолчанию
        default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "downloads")
        self.save_path_input.setText(default_path)
        self.logger.info(f"Установлен путь сохранения по умолчанию: {default_path}")
        
    def setup_general_tab(self):
        """Настройка вкладки 'Общие'"""
        layout = QVBoxLayout(self.general_tab)
        layout.setSpacing(12)  # Стандартный интервал как в ConversionTab
        layout.setContentsMargins(15, 15, 15, 15)  # Стандартные отступы как в ConversionTab
        
        # Единый стиль для всех QGroupBox
        group_box_style = """
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
        """
        
        # Группа "Настройки загрузки"
        download_group = QGroupBox(_("download_settings"))
        download_group.setStyleSheet(group_box_style)
        download_layout = QVBoxLayout(download_group)
        
        # URL видео
        url_layout = QHBoxLayout()
        url_label = QLabel(_("url_label"))
        url_label.setFixedWidth(120)
        url_label.setFixedHeight(30)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Вставьте URL видео для загрузки")
        self.url_input.setFixedHeight(30)
        
        self.fetch_info_button = QPushButton("Получить данные о видео")
        self.fetch_info_button.setFixedHeight(30)
        self.fetch_info_button.setFixedWidth(180)  # Увеличенная ширина для длинного текста
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.fetch_info_button)
        
        download_layout.addLayout(url_layout)
        
        # Информационная подпись под полем URL
        url_info_label = QLabel("Поддерживаются ссылки с YouTube, Kinescope и других популярных платформ")
        url_info_label.setStyleSheet("color: #666; font-size: 11px;")
        url_info_label.setWordWrap(True)
        download_layout.addWidget(url_info_label)
        
        layout.addWidget(download_group)
        
        # Разделитель
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator1)
        
        # Группа "Информация о видео"
        info_group = QGroupBox("Информация о видео")
        info_group.setStyleSheet(group_box_style)
        info_layout = QVBoxLayout(info_group)
        
        # Поля информации о видео
        self.video_title_label = QLabel("Название: ")
        self.video_author_label = QLabel("Автор: ")
        self.video_duration_label = QLabel("Длительность: ")
        
        info_layout.addWidget(self.video_title_label)
        info_layout.addWidget(self.video_author_label)
        info_layout.addWidget(self.video_duration_label)
        
        layout.addWidget(info_group)
        
        # Разделитель
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        
        # Группа "Выбор формата"
        format_group = QGroupBox("Выбор формата")
        format_group.setStyleSheet(group_box_style)
        format_layout = QVBoxLayout(format_group)
        
        # Выпадающий список для выбора формата
        format_selection_layout = QHBoxLayout()
        format_label = QLabel("Формат видео:")
        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(30)
        self.format_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
                color: #333333;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #0078d4;
            }
            QComboBox:focus {
                border-color: #0078d4;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                background-color: white;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #333333;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #cccccc;
                background-color: white;
                color: #333333;
                selection-background-color: #0078d4;
                selection-color: white;
            }
            QComboBox QAbstractItemView::item {
                padding: 5px;
                border: none;
                color: #333333;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e6f3ff;
                color: #333333;
            }
        """)
        self.format_combo.addItem("Выберите формат после получения данных о видео")
        self.format_combo.setEnabled(False)
        
        format_selection_layout.addWidget(format_label)
        format_selection_layout.addWidget(self.format_combo, 1)
        format_layout.addLayout(format_selection_layout)
        
        layout.addWidget(format_group)
        
        # Разделитель
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.HLine)
        separator3.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator3)
        
        # Группа "Настройки сохранения"
        save_group = QGroupBox("Настройки сохранения")
        save_group.setStyleSheet(group_box_style)
        save_group_layout = QVBoxLayout(save_group)
        
        # Выбор директории для сохранения
        save_layout = QHBoxLayout()
        save_label = QLabel(_("save_path_label"))
        save_label.setFixedWidth(120)
        save_label.setFixedHeight(30)
        
        self.save_path_input = QLineEdit()
        self.save_path_input.setPlaceholderText("Выберите папку для сохранения файлов")
        self.save_path_input.setFixedHeight(30)
        
        self.browse_button = QPushButton(_("browse_button"))
        self.browse_button.setFixedHeight(30)
        self.browse_button.setFixedWidth(100)  # Стандартная ширина как в ConversionTab
        
        save_layout.addWidget(save_label)
        save_layout.addWidget(self.save_path_input)
        save_layout.addWidget(self.browse_button)
        
        save_group_layout.addLayout(save_layout)
        
        # Информационная подпись для пути сохранения
        save_hint_label = QLabel("По умолчанию файлы сохраняются в папку Downloads")
        save_hint_label.setStyleSheet("color: #666; font-size: 11px;")
        save_hint_label.setWordWrap(True)
        save_group_layout.addWidget(save_hint_label)
        
        layout.addWidget(save_group)
        
        # Разделитель
        separator4 = QFrame()
        separator4.setFrameShape(QFrame.HLine)
        separator4.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator4)
        
        # Группа "Загрузка"
        download_action_group = QGroupBox("Загрузка")
        download_action_group.setStyleSheet(group_box_style)
        download_action_layout = QVBoxLayout(download_action_group)
        
        # Прогресс-бар
        self.general_progress_bar = QProgressBar()
        self.general_progress_bar.setFixedHeight(30)  # Стандартная высота как в ConversionTab
        self.general_progress_bar.setVisible(False)
        download_action_layout.addWidget(self.general_progress_bar)
        
        # Кнопка загрузки
        self.download_button = QPushButton(_("download_button"))
        self.download_button.setFixedHeight(30)
        download_action_layout.addWidget(self.download_button)
        
        layout.addWidget(download_action_group)
        
        # Подключение сигналов
        self.fetch_info_button.clicked.connect(self.fetch_video_info)
        self.browse_button.clicked.connect(self.browse_save_location)
        self.download_button.clicked.connect(self.start_download)
        
    def setup_kinescope_tab(self):
        """Настройка вкладки 'Kinescope'"""
        layout = QVBoxLayout(self.kinescope_tab)
        layout.setSpacing(12)  # Унифицированный интервал - точно как в General
        layout.setContentsMargins(15, 15, 15, 15)  # Унифицированные отступы - точно как в General
        
        # Область для перетаскивания файла (размещаем сверху) - фиксированная высота
        self.drop_area = QFrame()
        self.drop_area.setFrameShape(QFrame.StyledPanel)
        self.drop_area.setFrameShadow(QFrame.Sunken)
        self.drop_area.setFixedHeight(80)  # Уменьшенная высота для предотвращения наложений
        self.drop_area.setAcceptDrops(True)
        self.drop_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.drop_area.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
            QFrame:hover {
                border-color: #007acc;
                background-color: #f0f8ff;
            }
        """)
        
        drop_layout = QVBoxLayout(self.drop_area)
        drop_layout.setContentsMargins(10, 10, 10, 10)
        self.drop_label = QLabel(_("drag_drop_hint"))
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("color: #666; font-size: 12px; font-weight: 500;")
        self.drop_label.setFixedHeight(20)  # Уменьшенная высота для лейбла
        drop_layout.addWidget(self.drop_label)
        
        layout.addWidget(self.drop_area)
        
        # Информация о загруженном файле - фиксированная высота
        self.json_info_label = QLabel("")
        self.json_info_label.setWordWrap(True)
        self.json_info_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.json_info_label.setFixedHeight(20)  # Уменьшенная высота
        self.json_info_label.setStyleSheet("color: #007acc; font-weight: bold; margin: 3px 0; font-size: 11px;")
        layout.addWidget(self.json_info_label)
        
        # Разделитель - фиксированная высота
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setFixedHeight(2)  # Фиксированная высота
        layout.addWidget(separator)
        
        # Referrer - точно такие же настройки как в General
        referrer_layout = QHBoxLayout()
        referrer_label = QLabel(_("referrer_label"))
        referrer_label.setFixedWidth(120)  # Фиксированная ширина лейбла - как в General
        referrer_label.setFixedHeight(30)  # Фиксированная высота лейбла - как в General
        self.referrer_input = QLineEdit()
        self.referrer_input.setPlaceholderText("https://...")
        self.referrer_input.setFixedHeight(30)  # Фиксированная высота поля ввода - как в General
        referrer_layout.addWidget(referrer_label)
        referrer_layout.addWidget(self.referrer_input)
        layout.addLayout(referrer_layout)
        
        # URL видео - точно такие же настройки как в General
        video_url_layout = QHBoxLayout()
        video_url_label = QLabel(_("video_url_label"))
        video_url_label.setFixedWidth(120)  # Фиксированная ширина лейбла - как в General
        video_url_label.setFixedHeight(30)  # Фиксированная высота лейбла - как в General
        self.kinescope_url_input = QLineEdit()
        self.kinescope_url_input.setPlaceholderText("https://kinescope.io/... или прямая ссылка на .m3u8")
        self.kinescope_url_input.setFixedHeight(30)  # Фиксированная высота поля ввода - как в General
        video_url_layout.addWidget(video_url_label)
        video_url_layout.addWidget(self.kinescope_url_input)
        layout.addLayout(video_url_layout)
        
        # Имя файла - точно такие же настройки как в General
        filename_layout = QHBoxLayout()
        filename_label = QLabel(_("filename_label"))
        filename_label.setFixedWidth(120)  # Фиксированная ширина лейбла - как в General
        filename_label.setFixedHeight(30)  # Фиксированная высота лейбла - как в General
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("video_name")
        self.filename_input.setFixedHeight(30)  # Фиксированная высота поля ввода - как в General
        filename_layout.addWidget(filename_label)
        filename_layout.addWidget(self.filename_input)
        layout.addLayout(filename_layout)
        
        # Кодек с помощью - точно такие же настройки как в General
        codec_layout = QHBoxLayout()
        codec_label = QLabel(_("codec_label"))
        codec_label.setFixedWidth(120)  # Фиксированная ширина лейбла - как в General
        codec_label.setFixedHeight(30)  # Фиксированная высота лейбла - как в General
        self.kinescope_codec_combo = QComboBox()
        self.kinescope_codec_combo.addItems(["h264", "h265"])
        self.kinescope_codec_combo.setCurrentText("h264")
        self.kinescope_codec_combo.setFixedHeight(30)  # Фиксированная высота комбобокса - как в General
        self.kinescope_codec_help_button = QPushButton("?")
        self.kinescope_codec_help_button.setFixedSize(30, 30)  # Унифицированный размер кнопки помощи - как в General
        self.kinescope_codec_help_button.setToolTip(_("codec_help"))
        codec_layout.addWidget(codec_label)
        codec_layout.addWidget(self.kinescope_codec_combo)
        codec_layout.addWidget(self.kinescope_codec_help_button)
        layout.addLayout(codec_layout)
        
        # Выбор директории для сохранения - точно такие же настройки как в General
        save_layout = QHBoxLayout()
        save_label = QLabel(_("save_path_label"))
        save_label.setFixedWidth(120)  # Фиксированная ширина лейбла - как в General
        save_label.setFixedHeight(30)  # Фиксированная высота лейбла - как в General
        self.kinescope_save_path_input = QLineEdit()
        self.kinescope_save_path_input.setReadOnly(True)
        self.kinescope_save_path_input.setFixedHeight(30)  # Фиксированная высота поля ввода - как в General
        self.kinescope_save_path_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.kinescope_browse_button = QPushButton(_("browse_button"))
        self.kinescope_browse_button.setFixedHeight(30)  # Фиксированная высота кнопки - как в General
        self.kinescope_browse_button.setFixedWidth(100)  # Фиксированная ширина кнопки - как в General
        save_layout.addWidget(save_label)
        save_layout.addWidget(self.kinescope_save_path_input)
        save_layout.addWidget(self.kinescope_browse_button)
        layout.addLayout(save_layout)
        
        # Добавляем растягивающийся пробел для выравнивания кнопки загрузки внизу - как в General
        layout.addStretch()
        
        # Прогресс-бар для загрузки Kinescope
        self.kinescope_progress_bar = QProgressBar()
        self.kinescope_progress_bar.setVisible(False)
        self.kinescope_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.kinescope_progress_bar)
        
        # Кнопка загрузки - унифицированный стиль и позиционирование - как в General
        download_layout = QHBoxLayout()
        download_layout.addStretch()
        self.kinescope_download_button = QPushButton(_("download_button"))
        self.kinescope_download_button.setStyleSheet("""
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
        self.kinescope_download_button.setFixedHeight(40)  # Фиксированная высота кнопки - как в General
        self.kinescope_download_button.setFixedWidth(160)  # Фиксированная ширина кнопки - как в General
        download_layout.addWidget(self.kinescope_download_button)
        download_layout.addStretch()
        layout.addLayout(download_layout)
        
        # Устанавливаем путь сохранения по умолчанию
        default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "downloads")
        self.kinescope_save_path_input.setText(default_path)
    
    def setup_connections(self):
        """Настройка сигналов и слотов"""
        # Общие вкладки (browse_button и download_button уже подключены в setup_general_tab)
        self.fetch_info_button.clicked.connect(self.fetch_video_info)
        
        # Отслеживание изменений в поле URL
        self.url_input.textChanged.connect(self.on_url_changed)
        
        # Отслеживание выбора формата в выпадающем списке
        self.format_combo.currentTextChanged.connect(self.on_format_selection_changed)
        
        # Переключатель языка
        self.lang_toggle.language_changed.connect(self.change_language_from_toggle)
        
        # Kinescope вкладка
        self.kinescope_browse_button.clicked.connect(self.browse_kinescope_save_path)
        self.kinescope_download_button.clicked.connect(self.start_kinescope_download)
        # self.select_json_button.clicked.connect(self.select_json_file)  # удалено
        self.kinescope_codec_help_button.clicked.connect(self.show_codec_help)
        
        # Настройка обработки перетаскивания для drop_area
        self.drop_area.setAcceptDrops(True)
        self.drop_area.dragEnterEvent = self.dragEnterEvent
        self.drop_area.dropEvent = self.dropEvent
        self.drop_area.mousePressEvent = self.drop_area_clicked
        
        # Подключение сигналов новых вкладок к прогресс-бару
        # Удаляем старые подключения, так как теперь используем отдельные методы для каждой вкладки
        # self.audio_video_tab.progress_updated = self.update_progress
        # self.conversion_tab.progress_updated = self.update_progress
        
        # Изначально делаем элементы управления неактивными
        self.set_download_controls_enabled(False)
    
    def fetch_video_info(self):
        """Получает информацию о видео"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите URL видео")
            return
        
        if not self.validate_url(url):
            QMessageBox.warning(self, "Ошибка", "Неверный URL. Поддерживаются YouTube, Vimeo, Dailymotion и другие популярные платформы.")
            return
        
        # Отменяем предыдущий запрос, если он выполняется
        if self.video_info_worker and self.video_info_worker.isRunning():
            self.video_info_worker.cancel()
            self.video_info_worker.wait(3000)
        
        # Создаем новый worker
        self.video_info_worker = VideoInfoWorker(url)
        self.video_info_worker.info_fetched.connect(self.on_video_info_fetched)
        self.video_info_worker.error.connect(self.on_video_info_error)
        
        # Обновляем UI
        self.fetch_info_button.setEnabled(False)
        self.start_loading_animation()
        self.statusBar.showMessage("Получение информации о видео...")
        
        # Запускаем worker
        self.video_info_worker.start()
    
    @Slot(dict)
    def on_video_info_fetched(self, video_info):
        """Обработчик успешного получения информации о видео"""
        self.current_video_info = video_info
        self.video_info_fetched = True
        
        # Обновляем UI
        self.fetch_info_button.setEnabled(True)
        self.stop_loading_animation()
        
        # Отображаем информацию о видео
        title = video_info.get('title', 'Неизвестно')
        author = video_info.get('uploader', 'Неизвестно')
        duration = video_info.get('duration', 0)
        duration_str = f"{duration//60}:{duration%60:02d}" if duration else "Неизвестно"
        
        # Обновляем метки с информацией о видео
        self.video_title_label.setText(f"Название: {title}")
        self.video_author_label.setText(f"Автор: {author}")
        self.video_duration_label.setText(f"Длительность: {duration_str}")
        
        # Заполняем выпадающий список форматов
        self.format_combo.clear()  # Очищаем список
        formats = video_info.get('formats', [])
        
        # Сохраняем информацию о форматах для последующего использования
        self.formats_data = {}
        
        for format_info in formats:
            # Проверяем наличие аудиокодека
            acodec = format_info.get('acodec', 'none')
            
            # Пропускаем форматы без аудиокодека (только видео)
            if acodec == 'none' or not acodec:
                continue
            
            # Формат (расширение)
            ext = format_info.get('ext', 'Неизвестно')
            
            # Разрешение
            resolution = format_info.get('resolution', 'Неизвестно')
            
            # Размер
            filesize = format_info.get('filesize_approx', format_info.get('filesize', 0))
            filesize_str = self.format_filesize(filesize) if filesize else 'Неизвестно'
            
            # ID формата
            format_id = format_info.get('format_id', '')
            
            # Создаем текст для отображения в выпадающем списке с информацией об аудиокодеке
            display_text = f"{ext} - {resolution} ({filesize_str}) [аудио: {acodec}]"
            
            # Добавляем в выпадающий список
            self.format_combo.addItem(display_text)
            
            # Сохраняем данные формата для использования при загрузке
            self.formats_data[display_text] = {
                'format_id': format_id,
                'ext': ext,
                'resolution': resolution,
                'filesize': filesize_str,
                'acodec': acodec
            }
        
        # Активируем выпадающий список
        self.format_combo.setEnabled(True)
        
        # Кнопка загрузки будет активирована при выборе формата
        self.download_button.setEnabled(False)
        
        # Показываем информацию о видео в статусной строке
        self.statusBar.showMessage(f"Видео: {title[:50]} | Длительность: {duration_str}")
        
        self.logger.info(f"Информация о видео получена: {title}")
    
    @Slot(str)
    def on_video_info_error(self, error_message):
        """Обработчик ошибки получения информации о видео"""
        self.video_info_fetched = False
        self.current_video_info = None
        
        # Деактивируем элементы управления
        self.set_download_controls_enabled(False)
        
        # Обновляем UI
        self.fetch_info_button.setEnabled(True)
        self.stop_loading_animation()
        
        # Показываем ошибку
        QMessageBox.warning(self, "Ошибка", f"Не удалось получить информацию о видео:\n{error_message}")
        self.statusBar.showMessage("Готов")
        
        self.logger.error(f"Ошибка получения информации о видео: {error_message}")
    
    def on_url_changed(self):
        """Обработчик изменения URL"""
        # Сбрасываем состояние при изменении URL
        self.video_info_fetched = False
        self.current_video_info = None
        
        # Деактивируем элементы управления
        self.set_download_controls_enabled(False)
        
        # Очищаем выпадающий список форматов и деактивируем его
        if hasattr(self, 'format_combo'):
            self.format_combo.clear()
            self.format_combo.addItem("Выберите формат после получения данных о видео")
            self.format_combo.setEnabled(False)
            self.formats_data = {}
        
        # Обновляем статусную строку
        self.statusBar.showMessage(_("status_ready"))
        
    def on_format_selection_changed(self):
        """Обработчик выбора формата в выпадающем списке"""
        # Активируем кнопку загрузки только если выбран формат (не дефолтный текст)
        current_text = self.format_combo.currentText()
        is_valid_selection = (current_text != "Выберите формат после получения данных о видео" 
                             and current_text in self.formats_data)
        self.download_button.setEnabled(is_valid_selection)
    
    def update_format_options(self, video_info):
        """Обновляет доступные форматы на основе информации о видео (не используется с таблицей форматов)."""
        return
    
    def reset_format_options(self):
        """Сбрасывает форматы к значениям по умолчанию (не используется с таблицей форматов)."""
        return
    
    def set_download_controls_enabled(self, enabled):
        """Управляет активностью элементов управления загрузкой"""
        self.download_button.setEnabled(enabled)
        self.save_path_input.setEnabled(enabled)
        # Кнопка "Обзор" должна быть всегда активна для выбора пути сохранения
        # self.browse_button.setEnabled(enabled)  # Убираем эту строку
        # Включаем/отключаем выпадающий список форматов, если он существует
        if hasattr(self, 'format_combo'):
            self.format_combo.setEnabled(enabled)
    
    def browse_save_location(self):
        """Открывает диалог выбора директории для сохранения"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            _("dialog_title_browse"), 
            self.save_path_input.text()
        )
        if directory:
            self.save_path_input.setText(directory)
            self.logger.info(f"Выбран новый путь сохранения: {directory}")
            
    def browse_kinescope_save_path(self):
        """Выбор директории для сохранения для Kinescope"""
        directory = QFileDialog.getExistingDirectory(self, _("dialog_title_browse"))
        if directory:
            self.kinescope_save_path_input.setText(directory)
            self.logger.info(f"Выбрана директория для сохранения Kinescope: {directory}")
    
    def show_codec_help(self):
        """Показывает информационное сообщение о кодеках"""
        QMessageBox.information(
            self, 
            "Информация о кодеках", 
            """H.264 (AVC):
• Широко поддерживается всеми устройствами
• Хорошее соотношение качества и размера файла
• Рекомендуется для максимальной совместимости

AV1:
• Новый кодек с лучшим сжатием
• Лучшее качество при меньшем размере файла
• Может не поддерживаться старыми устройствами
• Рекомендуется для новых устройств и экономии места"""
        )
        
    def change_language(self, index):
        lang_code = self.lang_combo.itemData(index)
        if lang_code:
            self.logger.info(f"Попытка смены языка на: {lang_code}")
            localization = get_localization()
            if localization.set_language(lang_code):
                self.logger.info(f"Язык успешно изменен на: {lang_code}")
                QMessageBox.information(
                    self,
                    _("dialog_title_info"),
                    _("language_changed"),
                )
                # Правильный перезапуск приложения
                self.logger.info("Перезапуск приложения для применения нового языка")
                QApplication.instance().quit()
                # Получаем путь к main.py в корне проекта
                import __main__
                if hasattr(__main__, '__file__'):
                    main_script = os.path.abspath(__main__.__file__)
                else:
                    # Fallback для случаев, когда __main__.__file__ недоступен
                    main_script = os.path.abspath(sys.argv[0])
                QProcess.startDetached(sys.executable, [main_script])
            else:
                self.logger.error(f"Ошибка при смене языка на: {lang_code}")
                QMessageBox.critical(
                    self,
                    _("dialog_title_error"),
                    _("language_change_error"),
                )

    def change_language_from_toggle(self, lang_code):
        """Обработка смены языка от toggle switch"""
        localization = get_localization()
        if localization.set_language(lang_code):
            QMessageBox.information(
                self,
                _("dialog_title_info"),
                _("language_changed"),
            )
            # Правильный перезапуск приложения
            QApplication.instance().quit()
            # Получаем путь к main.py в корне проекта
            import __main__
            if hasattr(__main__, '__file__'):
                main_script = os.path.abspath(__main__.__file__)
            else:
                # Fallback для случаев, когда __main__.__file__ недоступен
                main_script = os.path.abspath(sys.argv[0])
            QProcess.startDetached(sys.executable, [main_script])
        else:
            QMessageBox.critical(
                self,
                _("dialog_title_error"),
                _("language_change_error"),
            )

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)
        
    def show_codec_help(self):
        """Показывает справку по кодекам"""
        help_text = """
<h3>Справка по кодекам видео</h3>

<p><b>H.264 (AVC)</b> - Рекомендуется для большинства случаев</p>
<ul>
<li>Хорошее качество при небольшом размере файла</li>
<li>Широкая совместимость с устройствами</li>
<li>Быстрое кодирование</li>
</ul>

<p><b>H.265 (HEVC)</b> - Для максимального качества</p>
<ul>
<li>Лучшее сжатие, меньший размер файла</li>
<li>Высокое качество видео</li>
<li>Медленнее кодирование</li>
</ul>

<p><b>VP9</b> - Открытый стандарт</p>
<ul>
<li>Хорошее сжатие</li>
<li>Бесплатный кодек</li>
<li>Поддержка веб-браузерами</li>
</ul>

<p><b>AV1</b> - Новейший стандарт</p>
<ul>
<li>Наилучшее сжатие</li>
<li>Открытый стандарт</li>
<li>Очень медленное кодирование</li>
</ul>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Справка по кодекам")
        msg.setText(help_text)
        msg.setTextFormat(Qt.RichText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
        
    def toggle_input_method(self, button):
        """Переключение между методами ввода для Kinescope"""
        if button == self.manual_input_radio:
            self.kinescope_manual_widget.setVisible(True)
            self.kinescope_json_widget.setVisible(False)
        else:
            self.kinescope_manual_widget.setVisible(False)
            self.kinescope_json_widget.setVisible(True)
            
    def drop_area_clicked(self, event):
        """Обработчик клика по области drag and drop для выбора файла"""
        self.select_json_file()
    
    def select_json_file(self):
        """Выбор JSON файла для Kinescope"""
        from core.localization import _
        file_path, filter_used = QFileDialog.getOpenFileName(
            self, 
            _("dialog_title_browse"), 
            "", 
            "JSON Files (*.json)"
        )
        if file_path:
            self.process_json_file(file_path)
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработка события перетаскивания файла"""
        if self.tab_widget.currentWidget() == self.kinescope_tab:
            mime_data = event.mimeData()
            if mime_data.hasUrls() and len(mime_data.urls()) == 1:
                url = mime_data.urls()[0]
                if url.isLocalFile() and url.toLocalFile().endswith('.json'):
                    event.acceptProposedAction()
                    
    def dropEvent(self, event: QDropEvent):
        """Обработка события сброса файла"""
        if self.tab_widget.currentWidget() == self.kinescope_tab:
            mime_data = event.mimeData()
            if mime_data.hasUrls() and len(mime_data.urls()) == 1:
                url = mime_data.urls()[0]
                if url.isLocalFile() and url.toLocalFile().endswith('.json'):
                    file_path = url.toLocalFile()
                    self.process_json_file(file_path)
                    event.acceptProposedAction()
                    
    def process_json_file(self, file_path):
        """Обработка JSON файла для Kinescope с визуальной анимацией загрузки"""
        try:
            # Показываем анимацию загрузки
            self.json_info_label.setText("🔄 Обработка файла...")
            self.json_info_label.setStyleSheet("color: #ff9500; font-weight: bold; margin: 5px 0;")
            
            # Обрабатываем файл через небольшую задержку для показа анимации
            QApplication.processEvents()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Извлекаем необходимые данные из JSON
            referrer = None
            shakahls = None
            
            # Поиск referrer и shakahls в JSON структуре
            if isinstance(data, dict):
                # Поиск referrer в корне JSON (строка 8)
                if 'referrer' in data:
                    referrer = data['referrer']
                
                # Рекурсивный поиск shakahls и m3u8 URL
                def find_m3u8_url(obj, path=""):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            # Приоритет для shakahls
                            if k == 'shakahls' and isinstance(v, str):
                                return v
                            elif isinstance(v, str) and '.m3u8' in v:
                                return v
                            elif isinstance(v, (dict, list)):
                                result = find_m3u8_url(v, f"{path}.{k}")
                                if result:
                                    return result
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            if isinstance(item, str) and '.m3u8' in item:
                                return item
                            elif isinstance(item, (dict, list)):
                                result = find_m3u8_url(item, f"{path}[{i}]")
                                if result:
                                    return result
                    return None
                
                shakahls = find_m3u8_url(data)
                
                # Обрезаем URL до .m3u8 включительно
                if shakahls and '.m3u8' in shakahls:
                    m3u8_index = shakahls.find('.m3u8')
                    if m3u8_index != -1:
                        shakahls = shakahls[:m3u8_index + 5]  # +5 для включения ".m3u8"
            
            if not shakahls:
                self.json_info_label.setText("❌ Не найден URL видео (.m3u8)")
                self.json_info_label.setStyleSheet("color: #ff4444; font-weight: bold; margin: 5px 0;")
                self.logger.warning(f"В JSON файле '{file_path}' не найден shakahls/m3u8 URL.")
                return
            
            # Автозаполнение полей
            if referrer:
                self.referrer_input.setText(referrer)
            
            if shakahls:
                self.kinescope_url_input.setText(shakahls)
            
            # Попытка извлечь имя файла из URL или использовать имя JSON файла
            filename = os.path.splitext(os.path.basename(file_path))[0]
            if not self.filename_input.text():
                self.filename_input.setText(filename)
            
            # Показываем успешное завершение
            self.json_info_label.setText(f"✅ Файл загружен: {os.path.basename(file_path)}")
            self.json_info_label.setStyleSheet("color: #007acc; font-weight: bold; margin: 5px 0;")
            self.logger.info(f"JSON файл '{file_path}' успешно загружен и обработан.")
            
        except json.JSONDecodeError:
            self.json_info_label.setText("❌ Ошибка: неверный формат JSON")
            self.json_info_label.setStyleSheet("color: #ff4444; font-weight: bold; margin: 5px 0;")
            self.logger.error(f"Ошибка декодирования JSON файла: {file_path}", exc_info=True)
        except Exception as e:
            self.json_info_label.setText(f"❌ Ошибка: {str(e)}")
            self.json_info_label.setStyleSheet("color: #ff4444; font-weight: bold; margin: 5px 0;")
            self.logger.error(f"Неизвестная ошибка при обработке JSON файла: {file_path}: {e}", exc_info=True)
            
    def validate_url(self, url: str) -> bool:
        """Валидация URL для проверки корректности ссылки"""
        if not url or not url.strip():
            return False
        
        # Базовая проверка URL
        try:
            parsed = urlparse(url.strip())
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Проверка на поддерживаемые протоколы
            if parsed.scheme not in ['http', 'https']:
                return False
                
            return True
        except Exception:
            return False
    
    def validate_kinescope_url(self, url: str) -> bool:
        """Специальная валидация для Kinescope URL"""
        if not self.validate_url(url):
            return False
            
        # Проверка на Kinescope домен
        parsed = urlparse(url.strip())
        kinescope_domains = ['kinescope.io', 'www.kinescope.io']
        
        return parsed.netloc.lower() in kinescope_domains
            
    def start_download(self):
        """Запускает процесс загрузки видео"""
        try:
            # Проверяем, не запущена ли уже загрузка
            if hasattr(self, 'download_worker') and self.download_worker and self.download_worker.isRunning():
                QMessageBox.warning(self, "Предупреждение", "Загрузка уже выполняется")
                return
                
            # Очищаем предыдущий worker если он существует
            if hasattr(self, 'download_worker') and self.download_worker:
                thread_manager.unregister_thread("download_worker")
                self.download_worker = None
                
            url = self.url_input.text()
            output_path = self.save_path_input.text()
            
            # Проверяем, что информация о видео была получена
            if not self.video_info_fetched:
                QMessageBox.warning(self, "Предупреждение", 
                                  "Сначала необходимо получить данные о видео, нажав кнопку 'Получить данные о видео'")
                return
            
            # Проверяем, что выбран формат в выпадающем списке
            current_text = self.format_combo.currentText()
            if (current_text == "Выберите формат после получения данных о видео" 
                or current_text not in self.formats_data):
                QMessageBox.warning(self, "Предупреждение", 
                                  "Пожалуйста, выберите формат для скачивания из выпадающего списка")
                return
                
            # Получаем ID формата из выбранного элемента
            format_id = self.formats_data[current_text]['format_id']
            
            # Улучшенная валидация URL
            if not url:
                QMessageBox.warning(self, _("dialog_title_warning"), _("error_empty_url"))
                return
                
            if not self.validate_url(url):
                QMessageBox.warning(self, _("dialog_title_warning"), "Некорректный URL. Пожалуйста, введите правильную ссылку.")
                return

            if not output_path:
                QMessageBox.warning(self, _("dialog_title_warning"), _("error_empty_save_path"))
                return
                
            # Проверка существования и доступности директории
            if not os.path.exists(output_path):
                try:
                    os.makedirs(output_path, exist_ok=True)
                except OSError as e:
                    QMessageBox.critical(self, _("dialog_title_error"), 
                                       f"Не удалось создать директорию для сохранения: {str(e)}")
                    return
            
            if not os.access(output_path, os.W_OK):
                QMessageBox.critical(self, _("dialog_title_error"), 
                                   "Нет прав на запись в выбранную директорию.")
                return
                
            self.logger.info(f"Начало загрузки: URL={url}, Path={output_path}, Format ID={format_id}")
            
            # Показываем прогресс-бар на вкладке "Общие"
            self.general_progress_bar.setVisible(True)
            self.general_progress_bar.setValue(0)
            self.set_ui_enabled(False)
            
            # Используем ID формата вместо опции формата и кодека
            self.download_worker = DownloadWorker(url, output_path, format_id)
            # Автоматическая регистрация потока происходит в BaseWorker.start()
            self.download_worker.progress_updated.connect(self.update_general_progress)
            self.download_worker.download_finished.connect(self.general_download_finished)
            self.download_worker.error.connect(self.download_error)
            self.download_worker.start()
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске загрузки: {e}")
            # Очищаем состояние при ошибке
            if hasattr(self, 'download_worker') and self.download_worker:
                thread_manager.unregister_thread("download_worker")
                self.download_worker = None
            self.set_ui_enabled(True)
            self.general_progress_bar.setVisible(False)
            QMessageBox.critical(self, _("dialog_title_error"), f"Ошибка при запуске загрузки: {str(e)}")
        
    def start_kinescope_download(self):
        """Запускает процесс загрузки видео с Kinescope"""
        # Получаем данные из полей
        referrer = self.referrer_input.text().strip()
        video_url = self.kinescope_url_input.text().strip()
        filename = self.filename_input.text().strip()
        output_path = self.kinescope_save_path_input.text().strip()
        
        self.logger.info(f"Начало загрузки Kinescope: URL={video_url}, Referrer={referrer}, Filename={filename}, Path={output_path}")
        codec = self.kinescope_codec_combo.currentText()
        
        # Проверяем обязательные поля
        if not output_path:
            QMessageBox.warning(self, _("dialog_title_warning"), _("error_empty_save_path"))
            return
            
        if not video_url:
            QMessageBox.warning(self, _("dialog_title_warning"), _("error_empty_url"))
            return
            
        # Формируем полный путь к файлу
        if filename:
            # Если указано имя файла, используем его
            if not filename.endswith(('.mp4', '.mkv', '.avi')):
                filename += '.mp4'  # Добавляем расширение по умолчанию
            full_output_path = os.path.join(output_path, filename)
        else:
            # Если имя файла не указано, используем путь как есть
            full_output_path = output_path
            
        # Логируем начало загрузки
        self.logger.info(f"Начало загрузки Kinescope: URL={video_url}, Path={full_output_path}, Referrer={referrer}, Codec={codec}")
        
        # Обновляем интерфейс
        # Показываем прогресс-бар на вкладке "Kinescope"
        self.kinescope_progress_bar.setVisible(True)
        self.kinescope_progress_bar.setValue(0)
        self.set_ui_enabled(False)
        
        # Запускаем загрузку с форматом "best"
        self.download_worker = DownloadWorker(
            video_url, 
            full_output_path, 
            "best",
            referrer=referrer if referrer else None
        )
        # Автоматическая регистрация потока происходит в BaseWorker.start()
        self.download_worker.progress_updated.connect(self.update_kinescope_progress)
        self.download_worker.download_finished.connect(self.kinescope_download_finished)
        self.download_worker.error.connect(self.download_error)
        self.download_worker.start()
            
    @Slot(float, str)
    def update_general_progress(self, progress, status_message):
        """Обновляет прогресс загрузки на вкладке 'Общие'"""
        self.general_progress_bar.setValue(int(progress))
        self.statusBar.showMessage(status_message)
        
    @Slot(float, str)
    def update_kinescope_progress(self, progress, status_message):
        """Обновляет прогресс загрузки на вкладке 'Kinescope'"""
        self.kinescope_progress_bar.setValue(int(progress))
        self.statusBar.showMessage(status_message)
        
    @Slot(bool, str)
    def general_download_finished(self, success, message):
        """Обрабатывает завершение загрузки на вкладке 'Общие'"""
        try:
            # Очищаем ссылку на worker и удаляем его из менеджера потоков
            if hasattr(self, 'download_worker') and self.download_worker:
                thread_manager.unregister_thread("download_worker")
                self.download_worker = None
                
            self.general_progress_bar.setVisible(False)
            self.set_ui_enabled(True)
            self.statusBar.showMessage(message)
            if success:
                self.logger.info(f"Загрузка успешно завершена: {message}")
                QMessageBox.information(self, _("dialog_title_info"), message)
            else:
                self.logger.error(f"Загрузка завершена с ошибкой: {message}")
                QMessageBox.critical(self, _("dialog_title_error"), message)
        except Exception as e:
            self.logger.error(f"Ошибка в general_download_finished: {e}")
            
    @Slot(bool, str)
    def kinescope_download_finished(self, success, message):
        """Обрабатывает завершение загрузки на вкладке 'Kinescope'"""
        try:
            # Очищаем ссылку на worker и удаляем его из менеджера потоков
            if hasattr(self, 'kinescope_download_worker') and self.kinescope_download_worker:
                thread_manager.unregister_thread("kinescope_download_worker")
                self.kinescope_download_worker = None
                
            self.kinescope_progress_bar.setVisible(False)
            self.set_ui_enabled(True)
            self.statusBar.showMessage(message)
            if success:
                self.logger.info(f"Загрузка Kinescope успешно завершена: {message}")
                QMessageBox.information(self, _("dialog_title_info"), message)
            else:
                self.logger.error(f"Загрузка Kinescope завершена с ошибкой: {message}")
                QMessageBox.critical(self, _("dialog_title_error"), message)
        except Exception as e:
            self.logger.error(f"Ошибка в kinescope_download_finished: {e}")
            
    @Slot(str)
    def download_error(self, message):
        """Обрабатывает ошибки загрузки"""
        try:
            self.logger.error(f"Ошибка во время загрузки: {message}")
            
            # Очищаем ссылки на workers при ошибке
            if hasattr(self, 'download_worker') and self.download_worker:
                thread_manager.unregister_thread("download_worker")
                self.download_worker = None
            if hasattr(self, 'kinescope_download_worker') and self.kinescope_download_worker:
                thread_manager.unregister_thread("kinescope_download_worker")
                self.kinescope_download_worker = None
                
            # Скрываем все прогресс-бары при ошибке
            if hasattr(self, 'general_progress_bar'):
                self.general_progress_bar.setVisible(False)
            if hasattr(self, 'kinescope_progress_bar'):
                self.kinescope_progress_bar.setVisible(False)
            self.set_ui_enabled(True)
            self.statusBar.showMessage(message)
            QMessageBox.critical(self, _("dialog_title_error"), message)
        except Exception as e:
            self.logger.error(f"Ошибка в download_error: {e}")
        
    def set_ui_enabled(self, enabled):
        """Включает/отключает элементы UI во время загрузки"""
        self.url_input.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)
        self.download_button.setEnabled(enabled)
        if hasattr(self, 'format_combo'):
            self.format_combo.setEnabled(enabled)
        
        # Элементы вкладки Kinescope
        self.kinescope_url_input.setEnabled(enabled)
        self.referrer_input.setEnabled(enabled)
        self.kinescope_browse_button.setEnabled(enabled)
        self.kinescope_download_button.setEnabled(enabled)
        self.kinescope_codec_combo.setEnabled(enabled)
        self.tab_widget.setEnabled(enabled)
        
    def closeEvent(self, event):
        """Обработка закрытия окна с принудительным завершением всех потоков"""
        active_workers = []
        
        # Собираем все активные потоки
        if hasattr(self, 'download_worker') and self.download_worker and self.download_worker.isRunning():
            active_workers.append(("загрузка", self.download_worker))
        
        if hasattr(self, 'conversion_tab') and self.conversion_tab:
            if hasattr(self.conversion_tab, 'conversion_worker') and self.conversion_tab.conversion_worker and self.conversion_tab.conversion_worker.isRunning():
                active_workers.append(("конвертация", self.conversion_tab.conversion_worker))
        
        if hasattr(self, 'audio_video_tab') and self.audio_video_tab:
            if hasattr(self.audio_video_tab, 'audio_video_worker') and self.audio_video_tab.audio_video_worker and self.audio_video_tab.audio_video_worker.isRunning():
                active_workers.append(("обработка аудио/видео", self.audio_video_tab.audio_video_worker))
        
        if active_workers:
            # Формируем сообщение о активных процессах
            processes = ', '.join([name for name, _ in active_workers])
            reply = QMessageBox.question(
                self, 
                _("dialog_title_warning"), 
                f"Выполняются процессы: {processes}.\nВы уверены, что хотите закрыть приложение?\n\nВсе активные операции будут принудительно завершены.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("Пользователь подтвердил выход, принудительно завершаем все потоки")
                self._force_terminate_all_threads()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def _force_terminate_all_threads(self):
        """Принудительно завершает все активные потоки"""
        # Завершаем все процессы FFmpeg
        try:
            from src.core.ffmpeg_processor import FFmpegProcessor
            FFmpegProcessor.terminate_all_processes()
        except Exception as e:
            self.logger.error(f"Ошибка при завершении процессов FFmpeg: {e}")
        
        # Используем централизованный менеджер потоков для завершения всех зарегистрированных потоков
        try:
            self.logger.info("Завершение всех потоков через менеджер потоков")
            thread_manager.terminate_all_threads()
        except Exception as e:
            self.logger.error(f"Ошибка при завершении потоков через менеджер: {e}")
        
        # Дополнительная проверка и завершение потоков, которые могли не быть зарегистрированы
        threads_to_terminate = []
        
        # Собираем все потоки для завершения
        if hasattr(self, 'download_worker') and self.download_worker:
            threads_to_terminate.append(("Download Worker", self.download_worker))
        
        if hasattr(self, 'conversion_tab') and self.conversion_tab:
            if hasattr(self.conversion_tab, 'worker') and self.conversion_tab.worker:
                threads_to_terminate.append(("Conversion Worker", self.conversion_tab.worker))
        
        if hasattr(self, 'audio_video_tab') and self.audio_video_tab:
            if hasattr(self.audio_video_tab, 'worker') and self.audio_video_tab.worker:
                threads_to_terminate.append(("AudioVideo Worker", self.audio_video_tab.worker))
        
        # Завершаем каждый поток (дополнительная проверка)
        for thread_name, thread in threads_to_terminate:
            try:
                if thread.isRunning():
                    self.logger.info(f"Дополнительное завершение потока: {thread_name}")
                    
                    # Пытаемся корректно остановить поток
                    if hasattr(thread, 'stop'):
                        thread.stop()
                    
                    # Мягкое завершение
                    thread.terminate()
                    
                    # Ждем завершения с таймаутом
                    if not thread.wait(1000):  # 1 секунда
                        self.logger.warning(f"Поток {thread_name} не отвечает, принудительно завершаем")
                        # В PySide6/PyQt нет метода kill(), используем terminate() повторно
                        thread.terminate()
                        thread.wait(500)  # Ждем еще полсекунды после terminate
                    
                    self.logger.info(f"Поток {thread_name} успешно завершен")
                    
            except Exception as e:
                self.logger.error(f"Ошибка при дополнительном завершении потока {thread_name}: {e}")
        
        self.logger.info("Завершение всех потоков завершено")

    def start_loading_animation(self):
        """Запускает анимацию загрузки на кнопке"""
        self.loading_dots = 0
        self.loading_timer.start(500)  # Обновление каждые 500мс
        
    def stop_loading_animation(self):
        """Останавливает анимацию загрузки и восстанавливает текст кнопки"""
        self.loading_timer.stop()
        self.fetch_info_button.setText(self.original_button_text)
        
    def update_loading_animation(self):
        """Обновляет анимацию загрузки (добавляет точки)"""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        spaces = " " * (3 - self.loading_dots)  # Добавляем пробелы для постоянной ширины
        self.fetch_info_button.setText(f"Загрузка{dots}{spaces}")


class LanguageToggle(QWidget):
    """Кастомный toggle switch для переключения языка"""
    language_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._slider_position = 0  # Инициализируем перед созданием анимации
        # Уменьшаем переключатель в 4 раза
        self.setFixedSize(30, 10)
        self.current_lang = "ru"  # По умолчанию русский
        self.animation = QPropertyAnimation(self, b"slider_position")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
    @Property(int)
    def slider_position(self):
        return self._slider_position
    
    @slider_position.setter
    def slider_position(self, value):
        self._slider_position = value
        self.update()
    
    def set_language(self, lang):
        """Установить текущий язык"""
        if lang != self.current_lang:
            self.current_lang = lang
            # В уменьшенной версии половина ширины зоны слайдера ~15
            target_pos = 15 if lang == "en" else 0
            self.animation.setStartValue(self._slider_position)
            self.animation.setEndValue(target_pos)
            self.animation.start()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Фон переключателя
        bg_color = QColor(240, 240, 240)
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 5, 5)
        
        # Активная область
        active_color = QColor(70, 130, 180)
        painter.setBrush(active_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self._slider_position, 1, 14, 8, 4, 4)
        
        # Текст
        painter.setPen(QColor(100, 100, 100))
        font = painter.font()
        font.setPointSize(6)
        font.setBold(True)
        painter.setFont(font)
        
        # Русский текст
        ru_color = QColor(255, 255, 255) if self.current_lang == "ru" else QColor(100, 100, 100)
        painter.setPen(ru_color)
        painter.drawText(QRect(1, 0, 12, 10), Qt.AlignCenter, "RU")
        
        # Английский текст
        en_color = QColor(255, 255, 255) if self.current_lang == "en" else QColor(100, 100, 100)
        painter.setPen(en_color)
        painter.drawText(QRect(17, 0, 12, 10), Qt.AlignCenter, "EN")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Порог половины для маленького переключателя
            new_lang = "en" if event.x() >= (self.width() // 2) else "ru"
            if new_lang != self.current_lang:
                self.set_language(new_lang)
                self.language_changed.emit(new_lang)