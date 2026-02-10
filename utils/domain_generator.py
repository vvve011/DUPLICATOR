import json
import random
import os
from typing import List, Set


class DomainGenerator:
    """Генератор уникальных доменных имен на основе оригинального домена"""
    
    def __init__(self, words_file: str = "data/domain_words.json"):
        """Инициализация генератора со словарем"""
        self.words_file = words_file
        self.load_dictionary()
        self.generated_domains: Set[str] = set()
    
    def load_dictionary(self):
        """Загрузка словаря из JSON файла"""
        try:
            with open(self.words_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.short_words = data.get('short_words', [])
                self.random_consonants = data.get('random_consonants', ['x', 'z', 'q', 'w', 'k'])
                self.random_vowels = data.get('random_vowels', ['a', 'e', 'i', 'o', 'u', 'y'])
                self.vowel_replacements = data.get('vowel_replacements', {})
        except FileNotFoundError:
            # Fallback если файл не найден
            self.short_words = ["bio", "pure", "care", "well", "zen", "lux", "nova", "via"]
            self.random_consonants = ['x', 'z', 'q', 'w', 'k']
            self.random_vowels = ['a', 'e', 'i', 'o', 'u', 'y']
            self.vowel_replacements = {}
    
    def extract_parts(self, domain: str) -> List[str]:
        """Извлечение частей из домена (3-6 символов)"""
        parts = []
        length = len(domain)
        
        # Извлекаем начало (3-6 символов)
        for i in range(3, min(7, length + 1)):
            parts.append(domain[:i])
        
        # Извлекаем конец (3-6 символов)
        for i in range(3, min(7, length + 1)):
            parts.append(domain[-i:])
        
        # Извлекаем середину если домен длинный
        if length > 6:
            mid_start = length // 3
            for i in range(3, 7):
                if mid_start + i <= length:
                    parts.append(domain[mid_start:mid_start + i])
        
        # Удаляем дубликаты и слишком короткие
        parts = list(set([p for p in parts if 3 <= len(p) <= 6]))
        
        return parts
    
    def strategy_prefix_original_plus_nutra(self, parts: List[str]) -> str:
        """Стратегия 1: Префикс оригинала + Nutra-слово"""
        part = random.choice(parts)
        nutra = random.choice(self.short_words)
        return part + nutra
    
    def strategy_nutra_plus_suffix_original(self, parts: List[str]) -> str:
        """Стратегия 2: Nutra-слово + Суффикс оригинала"""
        nutra = random.choice(self.short_words)
        part = random.choice(parts)
        return nutra + part
    
    def strategy_pure_nutra_combination(self) -> str:
        """Стратегия 3: Только Nutra-комбинации"""
        word1 = random.choice(self.short_words)
        word2 = random.choice(self.short_words)
        # Избегаем повторов одного и того же слова
        while word2 == word1:
            word2 = random.choice(self.short_words)
        return word1 + word2
    
    def strategy_triple_combination(self, parts: List[str]) -> str:
        """Стратегия 4: Тройная комбинация"""
        word1 = random.choice(self.short_words)
        word2 = random.choice(self.short_words)
        part = random.choice(parts) if parts else random.choice(self.short_words)
        
        combinations = [
            word1 + word2 + part[:3],  # Укороченная версия для длины
            word1 + part[:3] + word2[:3],
            part[:3] + word1 + word2[:3]
        ]
        
        return random.choice(combinations)
    
    def strategy_reverse_mutation(self, parts: List[str]) -> str:
        """Стратегия 5: Обратный порядок + мутация"""
        part = random.choice(parts)
        reversed_part = part[::-1][:4]  # Берем первые 4 символа от перевернутого
        nutra = random.choice(self.short_words)
        
        combinations = [
            reversed_part + nutra,
            nutra + reversed_part,
            reversed_part + nutra[:4]
        ]
        
        return random.choice(combinations)
    
    def strategy_consonant_insertion(self, parts: List[str]) -> str:
        """Стратегия 6: Вставка согласных между словами"""
        part = random.choice(parts)
        nutra = random.choice(self.short_words)
        consonant = random.choice(self.random_consonants)
        
        combinations = [
            part + consonant + nutra,
            nutra + consonant + part,
            part[:3] + consonant + nutra
        ]
        
        return random.choice(combinations)
    
    def strategy_vowel_mutation(self, parts: List[str]) -> str:
        """Стратегия 7: Мутация гласных"""
        part = random.choice(parts)
        nutra = random.choice(self.short_words)
        
        # Мутируем гласные в части оригинала
        mutated = list(part)
        for i, char in enumerate(mutated):
            if char in self.vowel_replacements and random.random() < 0.5:
                mutated[i] = random.choice(self.vowel_replacements[char])
        
        mutated_part = ''.join(mutated)
        
        combinations = [
            mutated_part + nutra,
            nutra + mutated_part,
        ]
        
        return random.choice(combinations)
    
    def validate_domain(self, domain: str) -> bool:
        """Проверка валидности домена"""
        # Длина 5-11 символов
        if not (5 <= len(domain) <= 11):
            return False
        
        # Только буквы английского алфавита
        if not domain.isalpha():
            return False
        
        # Должно быть минимум 2 гласные
        vowel_count = sum(1 for c in domain if c in 'aeiouAEIOU')
        if vowel_count < 2:
            return False
        
        # Не более 4 согласных подряд
        consonant_streak = 0
        for char in domain:
            if char.lower() not in 'aeiou':
                consonant_streak += 1
                if consonant_streak > 4:
                    return False
            else:
                consonant_streak = 0
        
        return True
    
    def generate_domain(self, original_domain: str, zone: str) -> str:
        """Генерация одного уникального домена"""
        # Очищаем оригинальный домен от зоны и специальных символов
        clean_domain = original_domain.lower()
        for ext in ['.com', '.net', '.org', '.ru', '.info', '.io', '.co']:
            clean_domain = clean_domain.replace(ext, '')
        
        # Удаляем www и http/https
        clean_domain = clean_domain.replace('www.', '').replace('http://', '').replace('https://', '')
        clean_domain = ''.join(c for c in clean_domain if c.isalpha())
        
        if len(clean_domain) < 3:
            clean_domain = "health"  # Fallback
        
        # Извлекаем части
        parts = self.extract_parts(clean_domain)
        
        # Список стратегий с весами
        strategies = [
            (self.strategy_prefix_original_plus_nutra, 30),
            (self.strategy_nutra_plus_suffix_original, 30),
            (self.strategy_pure_nutra_combination, 15),
            (self.strategy_triple_combination, 10),
            (self.strategy_reverse_mutation, 10),
            (self.strategy_consonant_insertion, 3),
            (self.strategy_vowel_mutation, 2)
        ]
        
        # Пытаемся сгенерировать уникальный домен
        max_attempts = 50
        for attempt in range(max_attempts):
            # Выбираем стратегию на основе весов
            strategy_list = []
            for strategy, weight in strategies:
                strategy_list.extend([strategy] * weight)
            
            chosen_strategy = random.choice(strategy_list)
            
            # Генерируем домен
            if chosen_strategy == self.strategy_pure_nutra_combination:
                new_domain = chosen_strategy()
            else:
                new_domain = chosen_strategy(parts)
            
            new_domain = new_domain.lower()
            
            # Проверяем валидность и уникальность
            full_domain = new_domain + zone
            if self.validate_domain(new_domain) and full_domain not in self.generated_domains:
                self.generated_domains.add(full_domain)
                return full_domain
        
        # Если не удалось сгенерировать - добавляем случайные символы
        base = random.choice(parts) if parts else "health"
        nutra = random.choice(self.short_words)
        suffix = random.choice(self.random_consonants)
        fallback = (base[:4] + nutra[:4] + suffix).lower()
        
        return fallback + zone
    
    def generate_domains(self, original_domain: str, count: int, zone: str) -> List[str]:
        """Генерация множества уникальных доменов"""
        domains = []
        
        for i in range(count):
            domain = self.generate_domain(original_domain, zone)
            domains.append(domain)
        
        return domains
    
    def reset(self):
        """Сброс кеша сгенерированных доменов"""
        self.generated_domains.clear()
