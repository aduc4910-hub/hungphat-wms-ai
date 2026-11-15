@echo off
cd /d "C:\Users\Lenovo\OneDrive\Tài liệu\Đề 4 Hưng phát"

REM Kiem tra cong 8088
netstat -ano | findstr :8088 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    exit /b 0
)

REM Tim Python
set "PYTHON_EXE="
if exist "C:\Users\Lenovo\AppData\Local\antigravity\python\5a1c45aafcb841ee\python.exe" (
    set "PYTHON_EXE=C:\Users\Lenovo\AppData\Local\antigravity\python\5a1c45aafcb841ee\python.exe"
)

if "%PYTHON_EXE%"=="" (
    for /d %%D in ("C:\Users\Lenovo\AppData\Local\antigravity\python\*") do (
        if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
    )
)

if "%PYTHON_EXE%"=="" (
    for /d %%D in ("C:\Users\Lenovo\AppData\Local\Programs\Python\*") do (
        if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
    )
)

if "%PYTHON_EXE%"=="" (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" app_server.py