@echo off
chcp 65001 >nul
title Сервер мастерской ТСОГ (Wi-Fi синхронизация)
cls
echo ======================================================================
echo   МАСТЕРСКАЯ ТСОГ — ЛОКАЛЬНЫЙ СЕРВЕР СИНХРОНИЗАЦИИ
echo ======================================================================
echo.
echo Проверка наличия Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python 3 не обнаружен на компьютере!
    echo Установите Python с официального сайта https://www.python.org/
    echo При установке обязательно поставьте галочку "Add Python to PATH".
    echo.
    pause
    exit /b
)

echo Запуск сервера на порту 8080...
echo.
python server.py
pause
