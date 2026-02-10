import re
import os
from typing import Optional, Dict
from collections import Counter
from charset_normalizer import from_path


class DomainDetector:
    """Автоматическое определение домена в файлах сайта"""
    
    def __init__(self):
        """Инициализация детектора"""
        # Паттерны для поиска доменов
        self.domain_patterns = [
            # С протоколом
            r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
            # Без протокола с www
            r'www\.([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
            # Только домен
            r'\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,})\b',
            # В кавычках
            r'["\']([a-zA-Z0-9-]+\.[a-zA-Z]{2,})["\']',
        ]
        
        # Расширения файлов для анализа
        self.text_extensions = {
            '.html', '.htm', '.php', '.css', '.js', '.txt', 
            '.json', '.xml', '.sql', '.conf', '.config',
            '.htaccess', '.env', '.ini', '.yaml', '.yml'
        }
        
        # Игнорируемые домены (CDN, популярные сервисы)
        self.ignore_domains = {
            'google.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'googleapis.com', 'jquery.com', 'bootstrap.com',
            'cloudflare.com', 'jsdelivr.net', 'unpkg.com', 'cdnjs.com',
            'fontawesome.com', 'fonts.google.com', 'w3.org', 'schema.org',
            'example.com', 'localhost', 'mailchimp.com', 'gstatic.com'
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
    
    def detect_domain_in_directory(self, directory: str) -> Optional[str]:
        """Определение основного домена в директории с файлами сайта"""
        domain_counter = Counter()
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
                
                # Извлекаем домены
                domains = self.extract_domains_from_text(content)
                
                # Очищаем и валидируем
                for domain in domains:
                    clean = self.clean_domain(domain)
                    if self.is_valid_domain(clean):
                        domain_counter[clean] += 1
        
        # Если ничего не найдено
        if not domain_counter:
            return None
        
        # Возвращаем самый частый домен
        most_common = domain_counter.most_common(1)[0][0]
        
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
