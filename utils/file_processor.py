import os
import re
from typing import Optional
from charset_normalizer import from_path


class FileProcessor:
    """Обработчик файлов для замены доменов"""
    
    def __init__(self):
        """Инициализация процессора"""
        # Расширения текстовых файлов для обработки
        self.text_extensions = {
            '.html', '.htm', '.php', '.css', '.js', '.txt',
            '.json', '.xml', '.sql', '.conf', '.config',
            '.htaccess', '.env', '.ini', '.yaml', '.yml',
            '.md', '.rst', '.py', '.java', '.cpp', '.c', '.h'
        }
        
        # Бинарные файлы которые пропускаем
        self.binary_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.zip', '.rar', '.7z', '.tar', '.gz',
            '.mp3', '.mp4', '.avi', '.mov', '.flv',
            '.exe', '.dll', '.so', '.dylib'
        }
    
    def is_text_file(self, filepath: str) -> bool:
        """Проверка, является ли файл текстовым"""
        _, ext = os.path.splitext(filepath)
        ext_lower = ext.lower()
        
        # Если явно бинарный - пропускаем
        if ext_lower in self.binary_extensions:
            return False
        
        # Если известный текстовый - обрабатываем
        if ext_lower in self.text_extensions:
            return True
        
        # Для неизвестных расширений - пробуем определить
        try:
            with open(filepath, 'rb') as f:
                chunk = f.read(512)
                # Проверяем наличие нулевых байтов (признак бинарного файла)
                if b'\x00' in chunk:
                    return False
            return True
        except Exception:
            return False
    
    def read_file_with_encoding(self, filepath: str) -> tuple:
        """
        Чтение файла с определением кодировки
        
        Returns:
            (content, encoding) или (None, None) при ошибке
        """
        # Пробуем определить кодировку
        try:
            result = from_path(filepath).best()
            if result:
                encoding = result.encoding
                content = str(result)
                return content, encoding
        except Exception:
            pass
        
        # Fallback - пробуем популярные кодировки
        for encoding in ['utf-8', 'cp1251', 'latin1', 'ascii', 'windows-1252']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                return content, encoding
            except Exception:
                continue
        
        return None, None
    
    def replace_domain_in_text(self, text: str, old_domain: str, new_domain: str) -> tuple:
        """
        Замена домена в тексте
        
        Args:
            text: исходный текст
            old_domain: старый домен (например, example.com)
            new_domain: новый домен (например, newsite.info)
            
        Returns:
            (modified_text, replacements_count)
        """
        # Очищаем домены от www и протокола для надежности
        old_clean = old_domain.replace('www.', '').replace('http://', '').replace('https://', '')
        new_clean = new_domain.replace('www.', '').replace('http://', '').replace('https://', '')
        
        # Извлекаем части нового домена (имя и зона)
        new_parts = new_clean.split('.')
        if len(new_parts) >= 2:
            new_name = '.'.join(new_parts[:-1])  # все кроме последней части
            new_zone = new_parts[-1]  # последняя часть (.com, .info и т.д.)
        else:
            new_name = new_clean
            new_zone = ''
        
        replacements = 0
        modified_text = text
        
        # Паттерны для замены (от более специфичных к общим)
        patterns = [
            # 1. С протоколом https://
            (re.compile(r'https?://(www\.)?' + re.escape(old_clean), re.IGNORECASE),
             lambda m: f"https://{new_clean}"),
            
            # 2. С www.
            (re.compile(r'\bwww\.' + re.escape(old_clean), re.IGNORECASE),
             lambda m: f"www.{new_clean}"),
            
            # 3. Просто домен в разных контекстах
            (re.compile(r'\b' + re.escape(old_clean) + r'\b', re.IGNORECASE),
             lambda m: new_clean),
            
            # 4. В email адресах (@domain.com)
            (re.compile(r'@' + re.escape(old_clean), re.IGNORECASE),
             lambda m: f"@{new_clean}"),
        ]
        
        for pattern, replacement in patterns:
            modified_text, count = pattern.subn(replacement, modified_text)
            replacements += count
        
        return modified_text, replacements
    
    def process_file(self, filepath: str, old_domain: str, new_domain: str) -> dict:
        """
        Обработка одного файла - замена домена
        
        Args:
            filepath: путь к файлу
            old_domain: старый домен
            new_domain: новый домен
            
        Returns:
            dict с результатами: {'success': bool, 'replacements': int, 'error': str}
        """
        result = {
            'success': False,
            'replacements': 0,
            'error': None
        }
        
        try:
            # Проверяем, текстовый ли файл
            if not self.is_text_file(filepath):
                result['success'] = True
                result['error'] = 'binary_file_skipped'
                return result
            
            # Читаем файл
            content, encoding = self.read_file_with_encoding(filepath)
            
            if content is None:
                result['error'] = 'cannot_read_file'
                return result
            
            # Заменяем домен
            modified_content, replacements = self.replace_domain_in_text(content, old_domain, new_domain)
            
            # Записываем обратно только если были изменения
            if replacements > 0:
                try:
                    with open(filepath, 'w', encoding=encoding or 'utf-8') as f:
                        f.write(modified_content)
                    
                    result['success'] = True
                    result['replacements'] = replacements
                except Exception as e:
                    result['error'] = f'cannot_write_file: {str(e)}'
            else:
                result['success'] = True
                result['replacements'] = 0
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def process_directory(self, directory: str, old_domain: str, new_domain: str) -> dict:
        """
        Обработка всей директории - замена домена во всех файлах
        
        Args:
            directory: путь к директории
            old_domain: старый домен
            new_domain: новый домен
            
        Returns:
            dict со статистикой обработки
        """
        stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'error_files': 0,
            'total_replacements': 0,
            'errors': []
        }
        
        # Обходим все файлы в директории
        for root, dirs, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                stats['total_files'] += 1
                
                # Обрабатываем файл
                result = self.process_file(filepath, old_domain, new_domain)
                
                if result['success']:
                    if result.get('error') == 'binary_file_skipped':
                        stats['skipped_files'] += 1
                    else:
                        stats['processed_files'] += 1
                        stats['total_replacements'] += result['replacements']
                else:
                    stats['error_files'] += 1
                    stats['errors'].append({
                        'file': filepath,
                        'error': result.get('error', 'unknown')
                    })
        
        return stats
