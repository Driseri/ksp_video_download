#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QComboBox, 
    QProgressBar, QFileDialog, QMessageBox, QStatusBar,
    QTabWidget, QRadioButton, QButtonGroup, QFrame, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QThread, QMimeData, QProcess, QPropertyAnimation, QEasingCurve, QRect, Property
from PySide6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent, QPainter, QColor, QPen

import json
import os

# Код для перезапуска приложения
RESTART_CODE = 1000

from src.core.downloader import VideoDownloader
from src.core.logger import get_logger
from src.core.localization import get_localization, _
from src.ui.audio_video_tab import AudioVideoTab
from src.ui.conversion_tab import ConversionTab


class DownloadWorker(QThread):
    """Рабочий поток для загрузки видео"""
    progress_updated = Signal(float, str)
    download_finished = Signal(bool, str)
    error = Signal(str)
    
    def __init__(self, url, output_path, format_option, codec="h264", referrer=None):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.format_option = format_option
        self.codec = codec
        self.referrer = referrer
        self.downloader = VideoDownloader()
        self.logger = get_logger()
    
    def run(self):
        try:
            self.logger.info(f"Начало загрузки видео: {self.url}")
            self.logger.info(f"Формат: {self.format_option}, кодек: {self.codec}, путь сохранения: {self.output_path}")
            
            result_file = self.downloader.download(
                self.url, 
                self.output_path, 
                self.format_option,
                progress_callback=self.progress_updated.emit,
                codec=self.codec,
                referrer=self.referrer
            )
            
            self.logger.info(f"Загрузка завершена успешно: {result_file}")
            self.download_finished.emit(True, _("status_complete").format(filename=os.path.basename(result_file)))
        except Exception as e:
            self.logger.error(f"Ошибка загрузки: {str(e)}", exc_info=True)
            self.error.emit(_("status_error").format(error=str(e)))


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        # Инициализация локализации перед использованием
        get_localization()
        
        self.logger = get_logger()
        self.logger.info("Инициализация главного окна приложения")
        
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
        
        # Прогресс загрузки
        progress_layout = QVBoxLayout()
        self.progress_label = QLabel(_("status_ready"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        main_layout.addLayout(progress_layout)
        
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
        layout.setSpacing(12)  # Унифицированный интервал
        layout.setContentsMargins(15, 15, 15, 15)  # Унифицированные отступы
        
        # URL видео - унифицированная высота
        url_layout = QHBoxLayout()
        url_label = QLabel(_("url_label"))
        url_label.setFixedWidth(120)  # Фиксированная ширина лейбла
        url_label.setFixedHeight(30)  # Фиксированная высота лейбла
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Вставьте URL видео для загрузки")
        self.url_input.setFixedHeight(30)  # Фиксированная высота поля ввода
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Выбор формата - унифицированная высота
        format_layout = QHBoxLayout()
        format_label = QLabel(_("format_label"))
        format_label.setFixedWidth(120)  # Фиксированная ширина лейбла
        format_label.setFixedHeight(30)  # Фиксированная высота лейбла
        self.format_combo = QComboBox()
        self.format_combo.addItem(_("format_best"), "best")
        self.format_combo.addItem(_("format_1080p"), "1080")
        self.format_combo.addItem(_("format_720p"), "720")
        self.format_combo.addItem(_("format_480p"), "480")
        self.format_combo.addItem(_("format_mp3"), "mp3")
        self.format_combo.addItem("Только аудио (M4A)", "m4a")
        self.format_combo.setFixedHeight(30)  # Фиксированная высота комбобокса
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)
        
        # Выбор кодека (AV1/H.264) - унифицированная высота
        codec_layout = QHBoxLayout()
        codec_label = QLabel("Кодек видео:")
        codec_label.setFixedWidth(120)  # Фиксированная ширина лейбла
        codec_label.setFixedHeight(30)  # Фиксированная высота лейбла
        self.codec_combo = QComboBox()
        self.codec_combo.addItem("H.264 (совместимость)", "h264")
        self.codec_combo.addItem("AV1 (лучшее качество)", "av1")
        self.codec_combo.setFixedHeight(30)  # Фиксированная высота комбобокса
        
        # Добавляем кнопку с вопросительным знаком для подсказки
        self.codec_help_button = QPushButton("?")
        self.codec_help_button.setFixedSize(30, 30)  # Унифицированный размер кнопки помощи
        self.codec_help_button.setToolTip("H.264: Лучшая совместимость с устройствами\nAV1: Лучшее качество при меньшем размере файла, но может не поддерживаться старыми устройствами")
        self.codec_help_button.clicked.connect(self.show_codec_help)
        
        codec_layout.addWidget(codec_label)
        codec_layout.addWidget(self.codec_combo)
        codec_layout.addWidget(self.codec_help_button)
        layout.addLayout(codec_layout)
        
        # Выбор директории для сохранения - унифицированная высота
        save_layout = QHBoxLayout()
        save_label = QLabel(_("save_path_label"))
        save_label.setFixedWidth(120)  # Фиксированная ширина лейбла
        save_label.setFixedHeight(30)  # Фиксированная высота лейбла
        self.save_path_input = QLineEdit()
        self.save_path_input.setReadOnly(True)
        self.save_path_input.setFixedHeight(30)  # Фиксированная высота поля ввода
        self.browse_button = QPushButton(_("browse_button"))
        self.browse_button.setFixedHeight(30)  # Фиксированная высота кнопки
        self.browse_button.setFixedWidth(100)  # Фиксированная ширина кнопки
        save_layout.addWidget(save_label)
        save_layout.addWidget(self.save_path_input)
        save_layout.addWidget(self.browse_button)
        layout.addLayout(save_layout)
        
        # Добавляем растягивающийся пробел для выравнивания кнопки загрузки внизу
        layout.addStretch()
        
        # Кнопка загрузки - унифицированный стиль и позиционирование
        download_layout = QHBoxLayout()
        download_layout.addStretch()
        self.download_button = QPushButton(_("download_button"))
        self.download_button.setStyleSheet("""
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
        self.download_button.setFixedHeight(40)  # Фиксированная высота кнопки
        self.download_button.setFixedWidth(160)  # Фиксированная ширина кнопки
        download_layout.addWidget(self.download_button)
        download_layout.addStretch()
        layout.addLayout(download_layout)
        
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
        
        # Кнопка загрузки - унифицированный стиль и позиционирование - точно как в General
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
        # Общие вкладки
        self.browse_button.clicked.connect(self.browse_save_location)
        self.download_button.clicked.connect(self.start_download)
        
        # Переключатель языка
        self.lang_toggle.language_changed.connect(self.change_language_from_toggle)
        
        # Kinescope вкладка
        self.kinescope_browse_button.clicked.connect(self.browse_kinescope_save_path)
        self.kinescope_download_button.clicked.connect(self.start_kinescope_download)
        # self.select_json_button.clicked.connect(self.select_json_file)  # удалено
        self.codec_help_button.clicked.connect(self.show_codec_help)
        self.kinescope_codec_help_button.clicked.connect(self.show_codec_help)
        
        # Настройка обработки перетаскивания для drop_area
        self.drop_area.setAcceptDrops(True)
        self.drop_area.dragEnterEvent = self.dragEnterEvent
        self.drop_area.dropEvent = self.dropEvent
        self.drop_area.mousePressEvent = self.drop_area_clicked
        
        # Подключение сигналов новых вкладок к прогресс-бару
        self.audio_video_tab.progress_updated = self.update_progress
        self.conversion_tab.progress_updated = self.update_progress
    
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
            
    def start_download(self):
        """Запускает процесс загрузки видео"""
        url = self.url_input.text()
        output_path = self.save_path_input.text()
        format_option = self.format_combo.currentData()
        codec = self.codec_combo.currentData()
        
        if not url:
            QMessageBox.warning(self, _("dialog_title_warning"), _("error_empty_url"))
            return
        
        if not output_path:
            QMessageBox.warning(self, _("dialog_title_warning"), _("error_empty_save_path"))
            return
            
        self.logger.info(f"Начало загрузки: URL={url}, Path={output_path}, Format={format_option}, Codec={codec}")
        self.progress_label.setText(_("status_starting_download"))
        self.progress_bar.setValue(0)
        self.set_ui_enabled(False)
        
        self.download_worker = DownloadWorker(url, output_path, format_option, codec)
        self.download_worker.progress_updated.connect(self.update_progress)
        self.download_worker.download_finished.connect(self.download_finished)
        self.download_worker.error.connect(self.download_error)
        self.download_worker.start()
        
    def start_kinescope_download(self):
        """Запускает процесс загрузки видео с Kinescope"""
        # Получаем данные из полей
        referrer = self.referrer_input.text().strip()
        video_url = self.kinescope_url_input.text().strip()
        filename = self.filename_input.text().strip()
        output_path = self.kinescope_save_path_input.text().strip()
        
        self.logger.info(f"Начало загрузки Kinescope: URL={video_url}, Referrer={referrer}, Filename={filename}, Path={output_path}")
        codec = self.codec_combo.currentText()
        
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
        self.progress_label.setText(_("status_starting_download"))
        self.progress_bar.setValue(0)
        self.set_ui_enabled(False)
        
        # Запускаем загрузку
        self.download_worker = DownloadWorker(
            video_url, 
            full_output_path, 
            "best", 
            codec, 
            referrer=referrer if referrer else None
        )
        self.download_worker.progress_updated.connect(self.update_progress)
        self.download_worker.download_finished.connect(self.download_finished)
        self.download_worker.error.connect(self.download_error)
        self.download_worker.start()
            
    @Slot(float, str)
    def update_progress(self, progress, status_message):
        """Обновляет прогресс бар и статус загрузки"""
        self.progress_bar.setValue(int(progress))
        self.progress_label.setText(status_message)
        self.statusBar.showMessage(status_message)
        
    @Slot(bool, str)
    def download_finished(self, success, message):
        """Обрабатывает завершение загрузки"""
        self.set_ui_enabled(True)
        self.progress_label.setText(message)
        self.statusBar.showMessage(message)
        if success:
            self.logger.info(f"Загрузка успешно завершена: {message}")
            QMessageBox.information(self, _("dialog_title_info"), message)
        else:
            self.logger.error(f"Загрузка завершена с ошибкой: {message}")
            QMessageBox.critical(self, _("dialog_title_error"), message)
            
    @Slot(str)
    def download_error(self, message):
        """Обрабатывает ошибки загрузки"""
        self.logger.error(f"Ошибка во время загрузки: {message}")
        self.set_ui_enabled(True)
        self.progress_label.setText(message)
        self.statusBar.showMessage(message)
        QMessageBox.critical(self, _("dialog_title_error"), message)
        
    def set_ui_enabled(self, enabled):
        """Включает/отключает элементы UI во время загрузки"""
        self.url_input.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.codec_combo.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)
        self.download_button.setEnabled(enabled)
        
        self.kinescope_url_input.setEnabled(enabled)
        self.referrer_input.setEnabled(enabled)
        self.kinescope_browse_button.setEnabled(enabled)
        self.kinescope_download_button.setEnabled(enabled)
        self.kinescope_codec_combo.setEnabled(enabled)
        self.tab_widget.setEnabled(enabled)
        
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if hasattr(self, 'download_worker') and self.download_worker.isRunning():
            reply = QMessageBox.question(
                self, 
                _("dialog_title_warning"), 
                _("confirm_exit_download_active"),
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.download_worker.terminate()
                self.download_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


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