#!/bin/bash

# DUPLICATOR - Скрипт запуска
echo "🌐 Запуск DUPLICATOR..."
echo ""

# Проверка установки зависимостей
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 Установка зависимостей..."
    pip3 install -r requirements.txt
    echo ""
fi

# Запуск приложения
echo "✅ Запуск Streamlit приложения..."
streamlit run app.py
