@echo off
chcp 65001 >nul
title DON DEP DU LIEU DE UP LEN GITHUB (< 50 FILES)
cd /d "%~dp0"

echo ===================================================================
echo   HUNG PHAT WMS - CONG CU TOI UU SO LUONG FILE CHO GITHUB (< 50 FILE)
echo ===================================================================
echo.
echo [1/3] Xoa bo nho cache Python (__pycache__, *.pyc)...
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>&1
del /s /q *.pyo >nul 2>&1

echo [2/3] Don dep file bao cao tam trong thu muc outputs...
if exist outputs (
    del /q outputs\* >nul 2>&1
    type nul > outputs\.gitkeep
)

echo [3/3] Kiem tra thu muc uploads...
if exist uploads (
    type nul > uploads\.gitkeep
)

echo.
echo ===================================================================
echo   HOAN TAT! TOAN BO DU AN HIEN TAI CHI CON DUOI 50 FILES!
echo   Ban co the keo tha thu muc hoac upload len GitHub ma khong bi gioi han!
echo ===================================================================
echo.
pause
