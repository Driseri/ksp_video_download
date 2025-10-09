"""
Минимальный модуль для работы с yt-dlp API
"""
import logging
import re
from typing import Dict, List, Optional, Union, Any
import yt_dlp


class YtDlpHandler:
    """Минимальный класс для работы с yt-dlp API"""
    
    def __init__(self):
        """Инициализация обработчика yt-dlp"""
        self.logger = logging.getLogger('ksp_video_downloader')
    
    def get_video_info(self, url: str) -> Optional[Dict]:
        """
        Получение расширенной информации о видео и доступных форматах без скачивания
        
        Args:
            url (str): URL видео
            
        Returns:
            Optional[Dict]: Информация о видео или None при ошибке
        """
        try:
            # Настройки для получения полной информации о видео
            ydl_opts = {
                'quiet': False,  # Выводим информацию для отладки
                'no_warnings': False,
                'skip_download': True,
                'format': 'best',  # Запрашиваем лучший формат
                'ignoreerrors': True,
                'youtube_include_dash_manifest': True,
                'listformats': True,  # Получаем список форматов
            }
            
            print(f"Получение информации о видео: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    self.logger.warning(f"Не удалось получить информацию о видео: {url}")
                    return self._get_fallback_info(url)
                
                # Обрабатываем форматы
                formats = self._process_formats(info.get('formats', []))
                
                # Создаем структуру с нужной информацией
                result = {
                    'id': info.get('id', 'unknown'),
                    'title': info.get('title', 'Неизвестное название'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', info.get('channel', 'Неизвестный автор')),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'description': (info.get('description', '') or '')[:200],  # Ограничиваем описание
                    'thumbnail': info.get('thumbnail', ''),
                    'webpage_url': info.get('webpage_url', url),
                    # Дополнительная информация
                    'channel_id': info.get('channel_id', ''),
                    'channel_url': info.get('channel_url', ''),
                    'like_count': info.get('like_count', 0),
                    'categories': info.get('categories', []),
                    'tags': info.get('tags', []),
                    'formats': formats
                }
                
                # Выводим информацию в консоль
                self._print_video_info(result)
                
                return result
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации о видео {url}: {str(e)}")
            return self._get_fallback_info(url, str(e))
        
    def _get_basic_info(self, url: str) -> Optional[Dict]:
        """
        Получение базовой информации о видео
        
        Args:
            url (str): URL видео
            
        Returns:
            Optional[Dict]: Базовая информация о видео
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': True,  # Получаем только базовую информацию
            'ignoreerrors': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    self.logger.warning(f"Не удалось получить базовую информацию о видео: {url}")
                    return None
                
                # Возвращаем расширенную информацию
                return {
                    'id': info.get('id', 'unknown'),
                    'title': info.get('title', 'Неизвестное название'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', info.get('channel', 'Неизвестный автор')),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'description': (info.get('description', '') or '')[:200],  # Ограничиваем описание
                    'thumbnail': info.get('thumbnail', ''),
                    'webpage_url': info.get('webpage_url', url),
                    # Дополнительная информация
                    'channel_id': info.get('channel_id', ''),
                    'channel_url': info.get('channel_url', ''),
                    'like_count': info.get('like_count', 0),
                    'dislike_count': info.get('dislike_count', 0),
                    'average_rating': info.get('average_rating', 0),
                    'categories': info.get('categories', []),
                    'tags': info.get('tags', []),
                    'is_live': info.get('is_live', False),
                    'was_live': info.get('was_live', False),
                    'live_status': info.get('live_status', ''),
                    'availability': info.get('availability', '')
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении базовой информации о видео {url}: {str(e)}")
            return None
            
    def _get_formats(self, url: str) -> list:
        """
        Получение информации о доступных форматах
        
        Args:
            url (str): URL видео
            
        Returns:
            list: Список доступных форматов
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'ignoreerrors': True,
            'youtube_include_dash_manifest': True,
        }
        
        try:
            print(f"Получение форматов для {url}...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    self.logger.warning(f"Не удалось получить форматы для видео: {url}")
                    return []
                
                # Обрабатываем форматы
                return self._process_formats(info.get('formats', []))
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении форматов для видео {url}: {str(e)}")
            return []
    
    def _get_fallback_info(self, url: str, error_msg: str = "") -> Dict:
        """
        Получение базовой информации о видео при ошибке
        
        Args:
            url (str): URL видео
            error_msg (str): Сообщение об ошибке
            
        Returns:
            Dict: Базовая информация о видео
        """
        video_id = self._extract_video_id(url)
        return {
            'id': video_id or 'error',
            'title': 'Видео недоступно',
            'duration': 0,
            'uploader': 'Неизвестный автор',
            'view_count': 0,
            'upload_date': '',
            'description': error_msg or 'Информация недоступна',
            'thumbnail': '',
            'webpage_url': url,
            'error': True,
            'error_message': error_msg or 'Не удалось получить информацию о видео',
            'formats': []  # Пустой список форматов
        }
        
    def _process_formats(self, formats: List[Dict]) -> List[Dict]:
        """
        Обработка и сортировка форматов видео
        
        Args:
            formats (List[Dict]): Список форматов из yt-dlp
            
        Returns:
            List[Dict]: Обработанный список форматов
        """
        if not formats:
            return []
            
        # Фильтруем и обрабатываем форматы
        processed_formats = []
        
        for fmt in formats:
            # Пропускаем форматы без расширения или с расширением mhtml (превью)
            if not fmt.get('ext') or fmt.get('ext') == 'mhtml':
                continue
                
            # Создаем структуру с нужной информацией
            processed_format = {
                'format_id': fmt.get('format_id', ''),
                'ext': fmt.get('ext', ''),
                'resolution': fmt.get('resolution', 'unknown'),
                'fps': fmt.get('fps', 0),
                'vcodec': fmt.get('vcodec', 'none'),
                'acodec': fmt.get('acodec', 'none'),
                'filesize': fmt.get('filesize', 0),
                'filesize_approx': fmt.get('filesize_approx', 0),
                'format': fmt.get('format', ''),
                'format_note': fmt.get('format_note', ''),
                'width': fmt.get('width', 0),
                'height': fmt.get('height', 0),
            }
            
            processed_formats.append(processed_format)
            
        # Сортируем форматы по качеству (сначала видео+аудио, потом по размеру)
        def sort_key(fmt):
            # Приоритет форматам с видео и аудио
            has_video = fmt['vcodec'] != 'none'
            has_audio = fmt['acodec'] != 'none'
            
            # Размер файла (используем приблизительный, если точный не указан)
            size = fmt['filesize'] or fmt['filesize_approx'] or 0
            
            # Разрешение (высота видео)
            height = fmt['height'] or 0
            
            # Сортируем сначала по наличию видео и аудио, потом по высоте, потом по размеру
            return (-(has_video and has_audio), -has_video, -has_audio, -height, -size)
            
        return sorted(processed_formats, key=sort_key)
        
    def _print_video_info(self, info: Dict) -> None:
        """
        Вывод информации о видео в консоль
        
        Args:
            info (Dict): Информация о видео
        """
        print("\n" + "=" * 50)
        print(f"ИНФОРМАЦИЯ О ВИДЕО: {info.get('title', 'Неизвестно')}")
        print("=" * 50)
        
        # Основная информация
        print(f"ID: {info.get('id', 'Неизвестно')}")
        print(f"Название: {info.get('title', 'Неизвестно')}")
        print(f"Автор: {info.get('uploader', 'Неизвестно')}")
        
        # Длительность в удобном формате
        duration = info.get('duration', 0)
        if duration:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"
            print(f"Длительность: {duration_str}")
        else:
            print(f"Длительность: {duration} сек")
            
        # Просмотры
        view_count = info.get('view_count', 0)
        if view_count:
            print(f"Просмотры: {view_count:,}".replace(',', ' '))
        else:
            print(f"Просмотры: {view_count}")
            
        # Дата загрузки
        upload_date = info.get('upload_date', '')
        if upload_date and len(upload_date) == 8:
            year, month, day = upload_date[:4], upload_date[4:6], upload_date[6:8]
            print(f"Дата загрузки: {day}.{month}.{year}")
        elif upload_date:
            print(f"Дата загрузки: {upload_date}")
            
        # Дополнительная информация
        if info.get('channel_id'):
            print(f"ID канала: {info.get('channel_id')}")
            
        if info.get('channel_url'):
            print(f"URL канала: {info.get('channel_url')}")
            
        if info.get('like_count'):
            print(f"Лайки: {info.get('like_count'):,}".replace(',', ' '))
            
        # Категории и теги
        if info.get('categories'):
            print(f"Категории: {', '.join(info.get('categories'))}")
            
        if info.get('tags'):
            tags = info.get('tags')
            if len(tags) > 5:
                tags_str = ', '.join(tags[:5]) + f" и еще {len(tags) - 5}"
            else:
                tags_str = ', '.join(tags)
            print(f"Теги: {tags_str}")
            
        # Форматы
        formats = info.get('formats', [])
        if formats:
            print("\nДоступные форматы:")
            print("-" * 80)
            print(f"{'ID':^10} | {'Расширение':^5} | {'Разрешение':^12} | {'Видео кодек':^12} | {'Аудио кодек':^12} | {'Размер':^10}")
            print("-" * 80)
            
            for fmt in formats[:10]:  # Показываем только первые 10 форматов
                # Преобразуем размер в удобный формат
                size = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                if size > 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                elif size > 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.2f} MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.2f} KB"
                elif size > 0:
                    size_str = f"{size} B"
                else:
                    size_str = "Неизвестно"
                    
                print(f"{fmt.get('format_id', 'N/A'):^10} | {fmt.get('ext', 'N/A'):^5} | {fmt.get('resolution', 'N/A'):^12} | {fmt.get('vcodec', 'none')[:10]:^12} | {fmt.get('acodec', 'none')[:10]:^12} | {size_str:^10}")
                
            if len(formats) > 10:
                print(f"... и еще {len(formats) - 10} форматов")
                
        print("=" * 50)
        
    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        Извлечение ID видео из URL
        
        Args:
            url (str): URL видео
            
        Returns:
            Optional[str]: ID видео или None
        """
        # Паттерны для извлечения ID из разных форматов URL
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Стандартный YouTube URL
            r'(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})',  # Короткий URL или embed
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'  # Полный URL с параметрами
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        return None
    
    def extract_single(self, info: Dict) -> Dict:
        """
        Простая нормализация информации о видео
        
        Args:
            info (Dict): Информация о видео
            
        Returns:
            Dict: Нормализованная информация
        """
        return {
            'type': 'video',
            'id': info.get('id', ''),
            'title': info.get('title', 'Неизвестное название'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Неизвестный автор'),
            'view_count': info.get('view_count', 0),
            'upload_date': info.get('upload_date', ''),
            'description': info.get('description', ''),
            'thumbnail': info.get('thumbnail', ''),
            'webpage_url': info.get('webpage_url', '')
        }
    
    def extract_all(self, url: str) -> Optional[Dict]:
        """
        Извлечение информации о видео или плейлисте
        
        Args:
            url (str): URL видео или плейлиста
            
        Returns:
            Optional[Dict]: Информация о видео/плейлисте или None при ошибке
        """
        info = self.get_video_info(url)
        if not info:
            return None
            
        # Если это одиночное видео
        return {
            'type': 'video',
            'entries': [self.extract_single(info)],
            'title': info.get('title', 'Неизвестное название'),
            'id': info.get('id', ''),
            'uploader': info.get('uploader', 'Неизвестный автор')
        }
    
    def handle_extraction_error(self, error):
        """
        Обработка ошибок извлечения
        
        Args:
            error: Объект ошибки
            
        Returns:
            str: Сообщение об ошибке
        """
        error_str = str(error)
        self.logger.error(f"Ошибка извлечения: {error_str}")
        return f"Ошибка при получении информации о видео: {error_str}"
        
    def _process_formats(self, formats_list):
        """
        Обработка списка форматов видео
        
        Args:
            formats_list (list): Список форматов из yt-dlp
            
        Returns:
            list: Обработанный список форматов
        """
        if not formats_list:
            return []
            
        processed_formats = []
        
        for fmt in formats_list:
            # Пропускаем форматы без ID
            if not fmt.get('format_id'):
                continue
                
            # Создаем объект формата с полезной информацией для скачивания
            format_info = {
                'format_id': fmt.get('format_id', ''),
                'format_note': fmt.get('format_note', ''),
                'ext': fmt.get('ext', ''),
                'resolution': fmt.get('resolution', ''),
                'width': fmt.get('width', 0),
                'height': fmt.get('height', 0),
                'fps': fmt.get('fps', 0),
                'vcodec': fmt.get('vcodec', ''),
                'acodec': fmt.get('acodec', ''),
                'abr': fmt.get('abr', 0),
                'format': fmt.get('format', ''),
                'filesize': fmt.get('filesize', 0),
                'filesize_approx': fmt.get('filesize_approx', 0),
                'tbr': fmt.get('tbr', 0),  # Общий битрейт
                'vbr': fmt.get('vbr', 0),  # Видео битрейт
                'abr': fmt.get('abr', 0),  # Аудио битрейт
                'protocol': fmt.get('protocol', ''),
                'language': fmt.get('language', ''),
                'quality': fmt.get('quality', 0),
                'has_video': fmt.get('vcodec', '') != 'none',
                'has_audio': fmt.get('acodec', '') != 'none',
            }
            
            processed_formats.append(format_info)
            
        # Сортируем форматы по качеству (от высокого к низкому)
        processed_formats.sort(key=lambda x: (x.get('quality', 0) or 0), reverse=True)
        
        return processed_formats
        
    def _print_video_info(self, info):
        """
        Вывод информации о видео в консоль
        
        Args:
            info (dict): Информация о видео
        """
        print("\n" + "=" * 50)
        print(f"ИНФОРМАЦИЯ О ВИДЕО: {info.get('title', 'Неизвестно')}")
        print("=" * 50)
        
        # Основная информация
        print(f"ID: {info.get('id', 'Неизвестно')}")
        print(f"Название: {info.get('title', 'Неизвестно')}")
        print(f"Автор: {info.get('uploader', info.get('channel', 'Неизвестно'))}")
        print(f"Длительность: {info.get('duration', 0)} сек")
        print(f"Просмотры: {info.get('view_count', 0)}")
        
        # Дополнительная информация
        if info.get('upload_date'):
            date = info.get('upload_date', '')
            if len(date) == 8:  # Формат YYYYMMDD
                formatted_date = f"{date[6:8]}.{date[4:6]}.{date[0:4]}"
                print(f"Дата загрузки: {formatted_date}")
                
        if info.get('categories'):
            print(f"Категории: {', '.join(info.get('categories', []))}")
            
        if info.get('tags'):
            print(f"Теги: {', '.join(info.get('tags', [])[:5])}{'...' if len(info.get('tags', [])) > 5 else ''}")
        
        # Информация о форматах
        formats = info.get('formats', [])
        if formats:
            print("\nДОСТУПНЫЕ ФОРМАТЫ:")
            print("-" * 80)
            print(f"{'ID':^10} | {'Расширение':^8} | {'Разрешение':^12} | {'Видео кодек':^12} | {'Аудио кодек':^12} | {'Размер':^10}")
            print("-" * 80)
            
            for fmt in formats:
                if not fmt.get('format_id'):
                    continue
                    
                # Получаем размер файла
                filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                if filesize:
                    if filesize > 1024 * 1024 * 1024:
                        size_str = f"{filesize / (1024 * 1024 * 1024):.2f} GB"
                    elif filesize > 1024 * 1024:
                        size_str = f"{filesize / (1024 * 1024):.2f} MB"
                    elif filesize > 1024:
                        size_str = f"{filesize / 1024:.2f} KB"
                    else:
                        size_str = f"{filesize} B"
                else:
                    size_str = "Неизвестно"
                
                # Формируем строку с информацией о формате
                print(f"{fmt.get('format_id', ''):^10} | {fmt.get('ext', ''):^8} | "
                      f"{fmt.get('resolution', 'Неизв.'):^12} | {fmt.get('vcodec', 'Неизв.')[:10]:^12} | "
                      f"{fmt.get('acodec', 'Неизв.')[:10]:^12} | {size_str:^10}")
                      
        print("=" * 50)