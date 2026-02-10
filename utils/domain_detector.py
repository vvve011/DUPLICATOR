import re
import os
from typing import Optional, Dict
from collections import Counter
from charset_normalizer import from_path


class DomainDetector:
    """Автоматическое определение домена в файлах сайта"""
    
    def __init__(self):
        """Инициализация детектора"""
        # Приоритетные паттерны (высокий вес)
        self.priority_patterns = [
            # Base URL в HTML
            (r'<base\s+href=["\'](https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', 100),
            # Canonical URL
            (r'<link\s+rel=["\']canonical["\']\s+href=["\'](https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', 90),
            # Open Graph URL
            (r'<meta\s+property=["\']og:url["\']\s+content=["\'](https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', 80),
            # WordPress site_url
            (r'["\']site_url["\']\s*[=:]\s*["\'](?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', 70),
            # define('WP_HOME' или define('WP_SITEURL'
            (r'define\(["\']WP_(?:HOME|SITEURL)["\']\s*,\s*["\'](?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', 70),
        ]
        
        # Обычные паттерны для поиска доменов
        self.domain_patterns = [
            # С протоколом
            r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
            # Без протокола с www
            r'www\.([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
            # В кавычках
            r'["\']([a-zA-Z0-9-]+\.[a-zA-Z]{2,})["\']',
            # Только домен (границы слов)
            r'\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,})\b',
        ]
        
        # Расширения файлов для анализа с весами
        self.file_weights = {
            '.html': 3,  # HTML файлы важнее
            '.htm': 3,
            '.php': 3,
            '.xml': 2,   # Конфиги важны
            '.conf': 2,
            '.config': 2,
            '.htaccess': 2,
            '.env': 2,
            '.ini': 2,
            '.css': 1,   # CSS/JS менее приоритетны
            '.js': 1,
            '.txt': 1,
            '.json': 1,
            '.sql': 1,
            '.yaml': 1,
            '.yml': 1,
        }
        
        self.text_extensions = set(self.file_weights.keys())
        
        # Расширенный список игнорируемых доменов
        self.ignore_domains = {
            # Google сервисы
            'google.com', 'googleapis.com', 'google-analytics.com', 'googletagmanager.com',
            'googlesyndication.com', 'doubleclick.net', 'gstatic.com', 'fonts.google.com',
            'maps.google.com', 'accounts.google.com',
            
            # Социальные сети
            'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 'linkedin.com',
            'pinterest.com', 'tiktok.com', 'snapchat.com', 'vk.com', 'ok.ru',
            'fb.com', 't.co', 'youtu.be',
            
            # CDN и библиотеки
            'cloudflare.com', 'jsdelivr.net', 'unpkg.com', 'cdnjs.com', 'cdn.jsdelivr.net',
            'stackpath.bootstrapcdn.com', 'maxcdn.bootstrapcdn.com', 'code.jquery.com',
            'ajax.googleapis.com', 'use.fontawesome.com', 'fontawesome.com',
            
            # Популярные сервисы
            'mailchimp.com', 'stripe.com', 'paypal.com', 'recaptcha.net',
            'w3.org', 'schema.org', 'creativecommons.org', 'wordpress.org',
            'example.com', 'example.net', 'example.org', 'localhost',
            
            # Метрики и аналитика
            'yandex.ru', 'yandex.com', 'metrika.yandex.ru', 'counter.yadro.ru',
            'mc.yandex.ru', 'top-fwz1.mail.ru', 'hotjar.com', 'crazyegg.com',
            
            # Прочие
            'gravatar.com', 'disqus.com', 'addthis.com', 'sharethis.com',
        }
    
    def is_text_file(self, filepath: str) -> bool:
        """Проверка, является ли файл текстовым"""
        _, ext = os.path.splitext(filepath)
        return ext.lower() in self.text_extensions
    
    def read_file_safely(self, filepath: str) -> Optional[str]:
        """Безопасное чтение файла с автоопределением кодировки"""
        try:
            # Пытаемся определить кодировку
            result = from_path(filepath).best()
            if result:
                return str(result)
        except Exception:
            pass
        
        # Fallback - пробуем разные кодировки
        for encoding in ['utf-8', 'cp1251', 'latin1', 'ascii']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read()
            except Exception:
                continue
        
        return None
    
    def extract_domains_from_text(self, text: str) -> list:
        """Извлечение доменов из текста"""
        domains = []
        
        for pattern in self.domain_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            domains.extend(matches)
        
        return domains
    
    def clean_domain(self, domain: str) -> str:
        """Очистка домена от лишних символов"""
        domain = domain.lower().strip()
        
        # Удаляем www
        domain = domain.replace('www.', '')
        
        # Удаляем порт если есть
        domain = re.sub(r':\d+', '', domain)
        
        # Удаляем путь если есть
        domain = domain.split('/')[0]
        
        return domain
    
    def is_valid_domain(self, domain: str) -> bool:
        """Проверка валидности домена"""
        # Минимальная длина
        if len(domain) < 4:
            return False
        
        # Должна быть точка
        if '.' not in domain:
            return False
        
        # Проверка формата
        parts = domain.split('.')
        if len(parts) < 2:
            return False
        
        # Проверка каждой части
        for part in parts:
            if not part or not re.match(r'^[a-zA-Z0-9-]+$', part):
                return False
        
        # Проверка зоны (должна быть только из букв)
        if not parts[-1].isalpha():
            return False
        
        # Игнорируем известные домены
        if domain in self.ignore_domains:
            return False
        
        return True
    
    def extract_priority_domains(self, text: str) -> Dict[str, int]:
        """Извлечение доменов из приоритетных паттернов с весами"""
        priority_domains = {}
        
        for pattern, weight in self.priority_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # В приоритетных паттернах домен может быть во второй группе
                domain = match[1] if isinstance(match, tuple) and len(match) > 1 else match
                if domain:
                    clean = self.clean_domain(domain)
                    if self.is_valid_domain(clean):
                        priority_domains[clean] = max(priority_domains.get(clean, 0), weight)
        
        return priority_domains
    
    def get_file_weight(self, filepath: str) -> int:
        """Получение веса файла по расширению"""
        _, ext = os.path.splitext(filepath)
        return self.file_weights.get(ext.lower(), 1)
    
    def is_subdomain(self, domain: str, base_domain: str) -> bool:
        """Проверка, является ли домен поддоменом базового домена"""
        return domain.endswith('.' + base_domain) or domain == base_domain
    
    def normalize_to_base_domain(self, domain: str) -> str:
        """Нормализация домена к базовому (удаление поддоменов)"""
        parts = domain.split('.')
        
        # Если больше 2 частей и не известные двухуровневые зоны
        if len(parts) > 2:
            # Список двухуровневых зон
            two_level_zones = ['co.uk', 'com.au', 'co.jp', 'com.br', 'co.za']
            
            # Проверяем последние две части
            last_two = '.'.join(parts[-2:])
            if last_two in two_level_zones:
                # Берем 3 последние части (subdomain.domain.co.uk)
                if len(parts) > 3:
                    return '.'.join(parts[-3:])
            else:
                # Берем 2 последние части (domain.com)
                return '.'.join(parts[-2:])
        
        return domain
    
    def extract_domain_from_filename(self, filename: str) -> Optional[str]:
        """
        Извлечение домена из названия файла/архива
        
        Примеры:
        - "example.com.zip" → "example.com"
        - "mysite.net_backup.rar" → "mysite.net"
        - "site-example-com.zip" → "example.com"
        - "example_com_2024.zip" → "example.com"
        """
        # Убираем расширение архива
        name = filename.lower()
        for ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.tar.gz']:
            name = name.replace(ext, '')
        
        # Убираем общие суффиксы
        for suffix in ['_backup', '-backup', '_archive', '-archive', '_site', '-site', 
                       '_www', '-www', '_web', '-web']:
            name = name.replace(suffix, '')
        
        # Убираем даты (2024, 20240102 и т.д.)
        name = re.sub(r'[_-]?\d{4,8}[_-]?', '', name)
        
        # Пробуем найти домен напрямую
        # Паттерн: что-то.зона (example.com)
        domain_match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', name)
        if domain_match:
            domain = domain_match.group(1)
            if self.is_valid_domain(domain):
                return self.clean_domain(domain)
        
        # Пробуем варианты с дефисами/подчеркиваниями вместо точек
        # site-example-com → site.example.com → example.com
        # example_com → example.com
        for separator in ['-', '_']:
            if separator in name:
                # Заменяем последний разделитель на точку (это может быть зона)
                parts = name.split(separator)
                if len(parts) >= 2:
                    # Пробуем последние 2-3 части
                    for i in range(min(3, len(parts)), 1, -1):
                        potential = '.'.join(parts[-i:])
                        if self.is_valid_domain(potential):
                            return self.clean_domain(potential)
        
        # Если не нашли - пробуем добавить популярные зоны
        if name and len(name) >= 3:
            for zone in ['com', 'net', 'org', 'ru', 'info']:
                potential = f"{name}.{zone}"
                if self.is_valid_domain(potential):
                    # Возвращаем без зоны, т.к. зона будет добавлена позже
                    return None
        
        return None
    
    def detect_domain_in_directory(self, directory: str) -> Optional[str]:
        """Определение основного домена в директории с файлами сайта (улучшенный алгоритм)"""
        # Счетчик с весами
        weighted_domains = Counter()
        priority_domains = {}
        files_analyzed = 0
        
        # Обходим все файлы в директории
        for root, dirs, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                
                # Проверяем только текстовые файлы
                if not self.is_text_file(filepath):
                    continue
                
                # Читаем файл
                content = self.read_file_safely(filepath)
                if not content:
                    continue
                
                files_analyzed += 1
                file_weight = self.get_file_weight(filepath)
                
                # Ищем приоритетные паттерны (только в HTML/PHP файлах)
                ext = os.path.splitext(filepath)[1].lower()
                if ext in ['.html', '.htm', '.php']:
                    prio_doms = self.extract_priority_domains(content)
                    for domain, weight in prio_doms.items():
                        priority_domains[domain] = max(priority_domains.get(domain, 0), weight)
                
                # Извлекаем обычные домены
                domains = self.extract_domains_from_text(content)
                
                # Очищаем и валидируем с весами
                for domain in domains:
                    clean = self.clean_domain(domain)
                    if self.is_valid_domain(clean):
                        # Нормализуем к базовому домену (удаляем поддомены)
                        base_domain = self.normalize_to_base_domain(clean)
                        weighted_domains[base_domain] += file_weight
        
        # Если нашли приоритетные домены - выбираем из них
        if priority_domains:
            # Сортируем по весу приоритета
            sorted_priority = sorted(priority_domains.items(), key=lambda x: x[1], reverse=True)
            # Берем домен с наивысшим приоритетом
            best_domain = sorted_priority[0][0]
            # Нормализуем
            return self.normalize_to_base_domain(best_domain)
        
        # Если приоритетных нет - берем по частоте с учетом весов
        if not weighted_domains:
            return None
        
        # Возвращаем самый частый домен с учетом весов
        most_common = weighted_domains.most_common(1)[0][0]
        
        return most_common
    
    def get_domain_statistics(self, directory: str) -> Dict[str, int]:
        """Получение статистики по всем найденным доменам"""
        domain_counter = Counter()
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                
                if not self.is_text_file(filepath):
                    continue
                
                content = self.read_file_safely(filepath)
                if not content:
                    continue
                
                domains = self.extract_domains_from_text(content)
                
                for domain in domains:
                    clean = self.clean_domain(domain)
                    if self.is_valid_domain(clean):
                        domain_counter[clean] += 1
        
        return dict(domain_counter)
