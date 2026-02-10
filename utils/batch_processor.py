import os
import shutil
from typing import List, Dict
from datetime import datetime

from .archive_handler import ArchiveHandler
from .domain_detector import DomainDetector
from .domain_generator import DomainGenerator
from .file_processor import FileProcessor
from .site_name_replacer import SiteNameReplacer


class BatchProcessor:
    """Пакетная обработка множества архивов"""
    
    def __init__(self):
        """Инициализация процессора"""
        self.archive_handler = ArchiveHandler()
        self.domain_detector = DomainDetector()
        self.domain_generator = DomainGenerator()
        self.file_processor = FileProcessor()
        self.site_name_replacer = SiteNameReplacer()
        
    def process_single_archive(self, archive_path: str, copies_count: int, 
                               domain_zone: str, temp_base_dir: str,
                               progress_callback=None) -> Dict:
        """
        Обработка одного архива с созданием копий
        
        Args:
            archive_path: путь к архиву
            copies_count: количество копий
            domain_zone: доменная зона (.com, .info и т.д.)
            temp_base_dir: базовая директория для временных файлов
            progress_callback: функция для обновления прогресса
            
        Returns:
            dict с результатами обработки
        """
        result = {
            'success': False,
            'archive_name': os.path.basename(archive_path),
            'original_domain': None,
            'generated_archives': [],
            'error': None,
            'stats': {}
        }
        
        archive_name = os.path.basename(archive_path)
        
        try:
            if progress_callback:
                progress_callback(f"Обработка {archive_name}: распаковка...")
            
            # 1. Создаем временную директорию для этого архива
            archive_temp_dir = os.path.join(temp_base_dir, f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
            extract_dir = os.path.join(archive_temp_dir, "extracted")
            
            # 2. Распаковываем архив
            if not self.archive_handler.extract_archive(archive_path, extract_dir):
                result['error'] = 'Ошибка распаковки архива'
                return result
            
            if progress_callback:
                progress_callback(f"Обработка {archive_name}: определение домена...")
            
            # 3. Определяем текущий домен
            # Сначала пробуем извлечь из названия архива (высокий приоритет!)
            domain_from_filename = self.domain_detector.extract_domain_from_filename(archive_name)
            
            if domain_from_filename and '.' in domain_from_filename:
                # Полный домен найден в названии архива (example.com) - используем его
                original_domain = domain_from_filename
                if progress_callback:
                    progress_callback(f"Обработка {archive_name}: домен из названия: {original_domain}")
            else:
                # Либо нет домена, либо только подсказка (dimvital)
                hint = domain_from_filename if domain_from_filename else None
                
                if progress_callback and hint:
                    progress_callback(f"Обработка {archive_name}: поиск с подсказкой '{hint}'...")
                
                # Ищем в файлах сайта с подсказкой из названия
                original_domain = self.domain_detector.detect_domain_in_directory(extract_dir, hint_from_filename=hint)
                
                if not original_domain:
                    result['error'] = 'Не удалось определить домен'
                    return result
            
            result['original_domain'] = original_domain
            
            # 3.5. Определяем название сайта
            if progress_callback:
                progress_callback(f"Обработка {archive_name}: определение названия сайта...")
            
            original_site_name = self.site_name_replacer.detect_site_name(extract_dir, original_domain)
            
            if progress_callback:
                progress_callback(f"Обработка {archive_name}: генерация доменов...")
            
            # 4. Генерируем новые домены
            new_domains = self.domain_generator.generate_domains(
                original_domain, 
                copies_count, 
                domain_zone
            )
            
            # 5. Создаем копии для каждого нового домена
            archives_created = []
            
            for idx, new_domain in enumerate(new_domains):
                if progress_callback:
                    progress_callback(f"Обработка {archive_name}: копия {idx+1}/{copies_count} ({new_domain})...")
                
                # Создаем директорию для копии
                copy_dir = os.path.join(archive_temp_dir, f"copy_{idx}")
                shutil.copytree(extract_dir, copy_dir)
                
                # Генерируем новое название из нового домена
                new_site_name = self.site_name_replacer.generate_site_name_from_domain(new_domain)
                
                # Заменяем домен и название сайта во всех файлах
                stats = self.file_processor.process_directory(
                    copy_dir, 
                    original_domain, 
                    new_domain,
                    original_site_name,
                    new_site_name
                )
                
                # Создаем архив из обработанной копии
                archive_name_output = self.archive_handler.get_archive_name_from_domain(new_domain)
                archive_output_path = os.path.join(archive_temp_dir, archive_name_output)
                
                if self.archive_handler.create_zip_archive(copy_dir, archive_output_path):
                    archives_created.append({
                        'path': archive_output_path,
                        'domain': new_domain,
                        'stats': stats
                    })
                
                # Удаляем директорию копии чтобы освободить место
                self.archive_handler.cleanup_directory(copy_dir)
            
            # 6. Сохраняем результаты
            result['success'] = True
            result['generated_archives'] = archives_created
            result['stats'] = {
                'copies_created': len(archives_created),
                'original_domain': original_domain
            }
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def process_multiple_archives(self, archives: List[str], copies_count: int,
                                  domain_zone: str, output_dir: str,
                                  progress_callback=None) -> Dict:
        """
        Обработка множества архивов
        
        Args:
            archives: список путей к архивам
            copies_count: количество копий для каждого архива
            domain_zone: доменная зона (.com, .info)
            output_dir: директория для сохранения результата
            progress_callback: функция для обновления прогресса
            
        Returns:
            dict с результатами обработки всех архивов
        """
        overall_result = {
            'success': False,
            'archives_processed': 0,
            'archives_failed': 0,
            'total_sites_created': 0,
            'master_archive_path': None,
            'results': [],
            'errors': []
        }
        
        try:
            # Создаем временную директорию
            temp_base_dir = self.archive_handler.get_temp_dir()
            all_generated_archives = []
            
            # Обрабатываем каждый архив
            for idx, archive_path in enumerate(archives):
                if progress_callback:
                    progress_callback(f"Архив {idx+1}/{len(archives)}: {os.path.basename(archive_path)}")
                
                # Обрабатываем архив
                result = self.process_single_archive(
                    archive_path,
                    copies_count,
                    domain_zone,
                    temp_base_dir,
                    progress_callback
                )
                
                overall_result['results'].append(result)
                
                if result['success']:
                    overall_result['archives_processed'] += 1
                    overall_result['total_sites_created'] += len(result['generated_archives'])
                    
                    # Собираем все созданные архивы
                    for archive_info in result['generated_archives']:
                        all_generated_archives.append(archive_info['path'])
                else:
                    overall_result['archives_failed'] += 1
                    overall_result['errors'].append({
                        'archive': os.path.basename(archive_path),
                        'error': result.get('error', 'Unknown error')
                    })
            
            if progress_callback:
                progress_callback("Создание главного архива...")
            
            # Создаем главный архив со всеми результатами
            if all_generated_archives:
                os.makedirs(output_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                master_archive_name = f"duplicates_{timestamp}.zip"
                master_archive_path = os.path.join(output_dir, master_archive_name)
                
                if self.archive_handler.create_master_archive(all_generated_archives, master_archive_path):
                    overall_result['master_archive_path'] = master_archive_path
                    overall_result['success'] = True
            
            # Очищаем временную директорию
            if progress_callback:
                progress_callback("Очистка временных файлов...")
            
            self.archive_handler.cleanup_directory(temp_base_dir)
            
        except Exception as e:
            overall_result['errors'].append({
                'archive': 'general',
                'error': str(e)
            })
        
        return overall_result
    
    def get_summary_text(self, result: Dict) -> str:
        """Генерация текстового резюме обработки"""
        lines = []
        
        lines.append("=" * 50)
        lines.append("РЕЗУЛЬТАТЫ ОБРАБОТКИ")
        lines.append("=" * 50)
        
        if result['success']:
            lines.append(f"✅ Обработка завершена успешно!")
            lines.append(f"")
            lines.append(f"📊 Статистика:")
            lines.append(f"  • Архивов обработано: {result['archives_processed']}")
            lines.append(f"  • Архивов с ошибками: {result['archives_failed']}")
            lines.append(f"  • Всего сайтов создано: {result['total_sites_created']}")
            
            if result['master_archive_path']:
                lines.append(f"")
                lines.append(f"📦 Главный архив:")
                lines.append(f"  {os.path.basename(result['master_archive_path'])}")
        else:
            lines.append(f"❌ Обработка завершена с ошибками")
        
        if result['errors']:
            lines.append(f"")
            lines.append(f"⚠️ Ошибки:")
            for error in result['errors']:
                lines.append(f"  • {error['archive']}: {error['error']}")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)
