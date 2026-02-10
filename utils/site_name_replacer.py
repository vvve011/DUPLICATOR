import re
import os
from typing import Optional, List, Tuple
from collections import Counter
from charset_normalizer import from_path


class SiteNameReplacer:
    """Класс для определения и замены названий сайта"""
    
    def __init__(self):
        """Инициализация"""
        self.text_extensions = {
            '.html', '.htm', '.php', '.css', '.js', '.txt',
            '.json', '.xml', '.sql', '.conf', '.config',
            '.htaccess', '.env', '.ini', '.yaml', '.yml'
        }
    
    def detect_site_name(self, directory: str, domain_hint: Optional[str] = None) -> Optional[str]:
        """
        Определение названия сайта из файлов
        
        Args:
            directory: директория с файлами сайта
            domain_hint: подсказка - домен сайта (для фильтрации)
            
        Returns:
            Название сайта или None
        """
        candidates = Counter()
        
        # Паттерны для поиска названия с приоритетами
        priority_patterns = [
            (r'<title>([^<|]+)', 100),  # <title>Название</title> или <title>Название | ...</title>
            (r'<meta\s+property=["\']og:site_name["\']\s+content=["\']([^"\']+)', 90),
            (r'<meta\s+name=["\']application-name["\']\s+content=["\']([^"\']+)', 85),
            (r'["\']blogname["\']\s*[=:]\s*["\']([^"\']+)', 70),
            (r'["\']site_title["\']\s*[=:]\s*["\']([^"\']+)', 70),
            (r'<h1[^>]*>([^<]+)</h1>', 50),
        ]
        
        # Собираем кандидатов из файлов
        for root, dirs, files in os.walk(directory):
            for filename in files:
                _, ext = os.path.splitext(filename)
                if ext.lower() not in self.text_extensions:
                    continue
                
                filepath = os.path.join(root, filename)
                content = self._read_file_safely(filepath)
                
                if not content:
                    continue
                
                # Применяем паттерны
                for pattern, weight in priority_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        name = match.strip()
                        # Очищаем от лишнего
                        name = re.sub(r'\s*[\|\-–—]\s*.*$', '', name)  # Убираем " | слоган"
                        name = name.strip()
                        
                        # Фильтруем слишком короткие или длинные
                        if 2 <= len(name) <= 50 and not self._is_generic_name(name):
                            candidates[name] += weight
        
        # Если есть подсказка домена - даем бонус совпадающим
        if domain_hint:
            domain_name = domain_hint.split('.')[0].lower()
            for name in list(candidates.keys()):
                if domain_name in name.lower() or name.lower() in domain_name:
                    candidates[name] += 500
        
        # Возвращаем самое частое
        if candidates:
            return candidates.most_common(1)[0][0]
        
        return None
    
    def generate_site_name_from_domain(self, domain: str) -> str:
        """
        Генерация названия сайта из домена
        
        Args:
            domain: домен (например, healcare.com)
            
        Returns:
            Название сайта (например, HealCare)
        """
        # Извлекаем имя без зоны
        name = domain.split('.')[0]
        
        # Пробуем разбить на части (CamelCase)
        # healcare -> Heal Care, biopure -> Bio Pure
        parts = self._split_camelcase(name)
        
        if len(parts) > 1:
            # Есть несколько частей - капитализируем каждую
            return ''.join(part.capitalize() for part in parts)
        else:
            # Одна часть - просто капитализируем
            return name.capitalize()
    
    def _split_camelcase(self, text: str) -> List[str]:
        """Разбивает текст на части (пытается найти составные слова)"""
        # Простая эвристика: ищем известные префиксы/суффиксы
        common_parts = [
            'bio', 'vita', 'pure', 'care', 'health', 'life', 'well', 'zen',
            'slim', 'fit', 'pro', 'max', 'neo', 'air', 'sun', 'lux', 'nova',
            'heal', 'medz', 'nutr', 'opti', 'rise', 'wave', 'zest', 'flex',
            'glow', 'herb', 'leaf', 'trim', 'calm', 'peak', 'zone', 'core'
        ]
        
        text_lower = text.lower()
        
        # Ищем совпадения в начале
        for part in common_parts:
            if text_lower.startswith(part) and len(text_lower) > len(part):
                rest = text[len(part):]
                return [text[:len(part)], rest]
        
        # Ищем совпадения в конце
        for part in common_parts:
            if text_lower.endswith(part) and len(text_lower) > len(part):
                start = text[:-len(part)]
                return [start, text[-len(part):]]
        
        # Не нашли - возвращаем как есть
        return [text]
    
    def replace_site_name_in_text(self, text: str, old_name: str, new_name: str) -> Tuple[str, int]:
        """
        Замена названия сайта в тексте
        
        Args:
            text: исходный текст
            old_name: старое название (например, "DimVital")
            new_name: новое название (например, "HealCare")
            
        Returns:
            (modified_text, replacements_count)
        """
        if not old_name or not new_name:
            return text, 0
        
        replacements = 0
        modified_text = text
        
        # Создаем варианты в разных регистрах
        variants = [
            (old_name, new_name),  # Оригинальный
            (old_name.lower(), new_name.lower()),  # lowercase
            (old_name.upper(), new_name.upper()),  # UPPERCASE
            (old_name.capitalize(), new_name.capitalize()),  # Capitalize
        ]
        
        # Убираем дубликаты
        variants = list(set(variants))
        
        for old_variant, new_variant in variants:
            if old_variant == new_variant:
                continue
            
            # Используем word boundaries для точной замены
            pattern = re.compile(r'\b' + re.escape(old_variant) + r'\b')
            modified_text, count = pattern.subn(new_variant, modified_text)
            replacements += count
        
        return modified_text, replacements
    
    def _read_file_safely(self, filepath: str) -> Optional[str]:
        """Безопасное чтение файла"""
        try:
            result = from_path(filepath).best()
            if result:
                return str(result)
        except Exception:
            pass
        
        for encoding in ['utf-8', 'cp1251', 'latin1', 'ascii']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read()
            except Exception:
                continue
        
        return None
    
    def _is_generic_name(self, name: str) -> bool:
        """Проверка на общие слова которые не являются названием"""
        generic_words = {
            'home', 'index', 'main', 'page', 'site', 'website', 'welcome',
            'test', 'demo', 'example', 'untitled', 'document', 'new page',
            'loading', 'error', '404', '403', '500'
        }
        
        return name.lower() in generic_words
