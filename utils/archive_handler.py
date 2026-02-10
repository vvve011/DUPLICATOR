import os
import zipfile
import rarfile
import shutil
from typing import Optional, List
import tempfile


class ArchiveHandler:
    """Обработчик архивов (ZIP, RAR)"""
    
    def __init__(self):
        """Инициализация обработчика"""
        # Настройка rarfile для использования unrar
        rarfile.UNRAR_TOOL = "unrar"
        # Пытаемся найти unrar, если не найден - используем альтернативный путь
        try:
            rarfile.tool_setup()
        except Exception:
            pass
    
    def get_archive_type(self, filepath: str) -> Optional[str]:
        """Определение типа архива по расширению"""
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == '.zip':
            return 'zip'
        elif ext == '.rar':
            return 'rar'
        else:
            return None
    
    def is_supported_archive(self, filepath: str) -> bool:
        """Проверка, поддерживается ли формат архива"""
        archive_type = self.get_archive_type(filepath)
        return archive_type in ['zip', 'rar']
    
    def extract_archive(self, archive_path: str, extract_to: str) -> bool:
        """
        Распаковка архива в указанную директорию
        
        Args:
            archive_path: путь к архиву
            extract_to: путь для распаковки
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Создаем директорию если не существует
            os.makedirs(extract_to, exist_ok=True)
            
            archive_type = self.get_archive_type(archive_path)
            
            if archive_type == 'zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                return True
                
            elif archive_type == 'rar':
                try:
                    with rarfile.RarFile(archive_path, 'r') as rar_ref:
                        rar_ref.extractall(extract_to)
                    return True
                except rarfile.NeedFirstVolume:
                    # Для многотомных архивов
                    return False
                except Exception as e:
                    # RAR может не работать на некоторых системах
                    print(f"Ошибка распаковки RAR: {e}")
                    return False
            
            return False
            
        except Exception as e:
            print(f"Ошибка при распаковке архива {archive_path}: {e}")
            return False
    
    def create_zip_archive(self, source_dir: str, output_path: str) -> bool:
        """
        Создание ZIP архива из директории
        
        Args:
            source_dir: директория с файлами
            output_path: путь для сохранения архива
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Создаем родительскую директорию если нужно
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Обходим все файлы в директории
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Вычисляем относительный путь
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
            
            return True
            
        except Exception as e:
            print(f"Ошибка при создании архива {output_path}: {e}")
            return False
    
    def create_master_archive(self, archives_list: List[str], output_path: str) -> bool:
        """
        Создание главного архива, содержащего другие архивы
        
        Args:
            archives_list: список путей к архивам
            output_path: путь для сохранения главного архива
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for archive_path in archives_list:
                    if os.path.exists(archive_path):
                        # Добавляем архив в главный архив
                        arcname = os.path.basename(archive_path)
                        zipf.write(archive_path, arcname)
            
            return True
            
        except Exception as e:
            print(f"Ошибка при создании главного архива: {e}")
            return False
    
    def get_archive_name_from_domain(self, domain: str) -> str:
        """
        Генерация имени архива из домена
        
        Args:
            domain: доменное имя (например, example.com)
            
        Returns:
            Имя файла архива (например, example.com.zip)
        """
        # Очищаем домен от недопустимых символов для имени файла
        safe_name = domain.replace('/', '_').replace('\\', '_')
        return f"{safe_name}.zip"
    
    def cleanup_directory(self, directory: str) -> bool:
        """
        Удаление директории и всего содержимого
        
        Args:
            directory: путь к директории
            
        Returns:
            True если успешно
        """
        try:
            if os.path.exists(directory):
                shutil.rmtree(directory)
            return True
        except Exception as e:
            print(f"Ошибка при удалении директории {directory}: {e}")
            return False
    
    def get_temp_dir(self) -> str:
        """Создание временной директории"""
        return tempfile.mkdtemp(prefix="duplicator_")
