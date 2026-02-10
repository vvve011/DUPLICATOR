import streamlit as st
import os
import tempfile
from utils.batch_processor import BatchProcessor


# Настройка страницы
st.set_page_config(
    page_title="DUPLICATOR - Клонирование сайтов",
    page_icon="🌐",
    layout="wide"
)

# Инициализация session state
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'result' not in st.session_state:
    st.session_state.result = None


def main():
    """Главная функция приложения"""
    
    # Заголовок
    st.title("🌐 DUPLICATOR - Клонирование сайтов")
    st.markdown("---")
    
    # Описание
    with st.expander("ℹ️ Как использовать", expanded=False):
        st.markdown("""
        ### Инструкция:
        1. **Загрузите архивы** (ZIP или RAR) с сайтами
        2. **Выберите доменную зону** (.com или .info)
        3. **Укажите количество копий** для каждого архива
        4. **Нажмите "Создать дубликаты"**
        5. **Скачайте главный архив** с результатами
        
        ### Что делает приложение:
        - Автоматически определяет текущий домен в файлах
        - Генерирует уникальные названия доменов (5-11 символов, без цифр)
        - Заменяет старый домен на новый во всех текстовых файлах
        - Создает архивы для каждой копии (имя архива = новый домен)
        - Упаковывает все в один главный архив
        """)
    
    # Основной интерфейс
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📤 Загрузка архивов")
        uploaded_files = st.file_uploader(
            "Выберите архивы сайтов (ZIP/RAR)",
            type=['zip', 'rar'],
            accept_multiple_files=True,
            help="Можно загрузить несколько архивов одновременно"
        )
        
        if uploaded_files:
            st.success(f"✅ Загружено архивов: {len(uploaded_files)}")
            
            # Отображаем список загруженных файлов
            with st.expander("Просмотр загруженных файлов"):
                for idx, file in enumerate(uploaded_files, 1):
                    file_size = file.size / 1024 / 1024  # в MB
                    st.write(f"{idx}. **{file.name}** ({file_size:.2f} MB)")
    
    with col2:
        st.subheader("⚙️ Настройки")
        
        # Выбор доменной зоны
        domain_zone = st.radio(
            "Доменная зона:",
            options=['.com', '.info'],
            horizontal=True
        )
        
        # Количество копий
        copies_count = st.number_input(
            "Копий на архив:",
            min_value=1,
            max_value=100,
            value=5,
            step=1,
            help="Сколько копий создать для каждого загруженного архива"
        )
        
        st.markdown("---")
        
        # Информация о том, что будет создано
        if uploaded_files:
            total_sites = len(uploaded_files) * copies_count
            st.info(f"📊 Будет создано: **{total_sites}** сайт(ов)")
    
    st.markdown("---")
    
    # Кнопка запуска
    if uploaded_files:
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn2:
            if st.button("🚀 Создать дубликаты", type="primary", use_container_width=True):
                process_archives(uploaded_files, copies_count, domain_zone)
    else:
        st.warning("⚠️ Загрузите архивы для начала работы")
    
    # Отображение результатов
    if st.session_state.processed and st.session_state.result:
        display_results()


def process_archives(uploaded_files, copies_count, domain_zone):
    """Обработка загруженных архивов"""
    
    # Создаем временную директорию для загруженных файлов
    temp_input_dir = tempfile.mkdtemp(prefix="duplicator_input_")
    temp_output_dir = tempfile.mkdtemp(prefix="duplicator_output_")
    
    try:
        # Сохраняем загруженные файлы
        archive_paths = []
        
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        progress_text.text("Сохранение загруженных файлов...")
        
        for idx, uploaded_file in enumerate(uploaded_files):
            file_path = os.path.join(temp_input_dir, uploaded_file.name)
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            archive_paths.append(file_path)
            
            progress = (idx + 1) / len(uploaded_files) * 0.1  # 10% на загрузку
            progress_bar.progress(progress)
        
        # Обработка архивов
        processor = BatchProcessor()
        
        progress_info = {
            'current': 0,
            'total': len(archive_paths) * copies_count
        }
        
        def update_progress(message):
            """Callback для обновления прогресса"""
            progress_text.text(message)
            progress_info['current'] += 1
            progress_value = 0.1 + (progress_info['current'] / progress_info['total']) * 0.9
            progress_bar.progress(min(progress_value, 1.0))
        
        # Запускаем обработку
        result = processor.process_multiple_archives(
            archives=archive_paths,
            copies_count=copies_count,
            domain_zone=domain_zone,
            output_dir=temp_output_dir,
            progress_callback=update_progress
        )
        
        progress_bar.progress(1.0)
        progress_text.text("✅ Обработка завершена!")
        
        # Сохраняем результат в session state
        st.session_state.result = result
        st.session_state.processed = True
        
        # Перерисовываем страницу
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Ошибка при обработке: {str(e)}")


def display_results():
    """Отображение результатов обработки"""
    
    result = st.session_state.result
    
    st.markdown("---")
    st.subheader("📊 Результаты обработки")
    
    if result['success']:
        # Успешная обработка
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Обработано архивов", result['archives_processed'])
        
        with col2:
            st.metric("Создано сайтов", result['total_sites_created'])
        
        with col3:
            st.metric("Ошибок", result['archives_failed'])
        
        # Кнопка скачивания
        if result['master_archive_path'] and os.path.exists(result['master_archive_path']):
            st.markdown("---")
            st.success("✅ Главный архив готов к скачиванию!")
            
            with open(result['master_archive_path'], 'rb') as f:
                archive_data = f.read()
            
            col_download1, col_download2, col_download3 = st.columns([1, 1, 1])
            with col_download2:
                st.download_button(
                    label="⬇️ Скачать главный архив",
                    data=archive_data,
                    file_name=os.path.basename(result['master_archive_path']),
                    mime="application/zip",
                    use_container_width=True,
                    type="primary"
                )
        
        # Детальная информация по каждому архиву
        st.markdown("---")
        st.subheader("📋 Детали по архивам")
        
        for idx, archive_result in enumerate(result['results'], 1):
            with st.expander(f"Архив {idx}: {archive_result['archive_name']}"):
                if archive_result['success']:
                    st.success(f"✅ Обработан успешно")
                    st.write(f"**Оригинальный домен:** {archive_result['original_domain']}")
                    st.write(f"**Создано копий:** {len(archive_result['generated_archives'])}")
                    
                    # Список сгенерированных доменов
                    if archive_result['generated_archives']:
                        st.write("**Сгенерированные домены:**")
                        domains = [info['domain'] for info in archive_result['generated_archives']]
                        
                        # Отображаем в несколько колонок
                        cols = st.columns(3)
                        for i, domain in enumerate(domains):
                            with cols[i % 3]:
                                st.write(f"• {domain}")
                else:
                    st.error(f"❌ Ошибка: {archive_result.get('error', 'Неизвестная ошибка')}")
    
    else:
        st.error("❌ Обработка завершена с ошибками")
        
        if result['errors']:
            st.subheader("⚠️ Список ошибок:")
            for error in result['errors']:
                st.write(f"• **{error['archive']}**: {error['error']}")
    
    # Кнопка для новой обработки
    st.markdown("---")
    col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])
    with col_reset2:
        if st.button("🔄 Создать новые дубликаты", use_container_width=True):
            st.session_state.processed = False
            st.session_state.result = None
            st.rerun()


# Запуск приложения
if __name__ == "__main__":
    main()
