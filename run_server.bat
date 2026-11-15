@echo off
chcp 65001 >nul
title HUNG PHAT SMART WAREHOUSE - MASTER AI AGENT
cd /d "%~dp0"

echo ===================================================================
echo   HUNG PHAT SMART WAREHOUSE - HE THONG TRO LY AI QUAN LY KHO
echo   Web Dashboard: http://localhost:8088
echo ===================================================================
echo.

REM Kiem tra cong 8088 da chay chua
netstat -ano | findstr :8088 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo [THONG BAO] May chu dang chay tren cong 8088!
    echo Dang mo trinh duyet tai http://localhost:8088...
    start http://localhost:8088
    ping -n 3 127.0.0.1 >nul
    exit /b 0
)

REM Tim duong dan Python
set "PYTHON_BIN="

if exist "C:\Users\Lenovo\AppData\Local\antigravity\python\5a1c45aafcb841ee\python.exe" (
    set "PYTHON_BIN=C:\Users\Lenovo\AppData\Local\antigravity\python\5a1c45aafcb841ee\python.exe"
)

if "%PYTHON_BIN%"=="" (
    for /d %%D in ("C:\Users\Lenovo\AppData\Local\antigravity\python\*") do (
        if exist "%%D\python.exe" set "PYTHON_BIN=%%D\python.exe"
    )
)

if "%PYTHON_BIN%"=="" (
    for /d %%D in ("C:\Users\Lenovo\AppData\Local\Programs\Python\*") do (
        if exist "%%D\python.exe" set "PYTHON_BIN=%%D\python.exe"
    )
)

if "%PYTHON_BIN%"=="" (
    set "PYTHON_BIN=python"
)

echo [1/3] Su dung Python: %PYTHON_BIN%
echo [2/3] Dang khoi dong may chu HTTP (Port 8088)...

REM Tu dong tao file khoi dong cung Windows neu chua co
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup" (
    if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\HungPhat_WMS_AutoStart.vbs" (
        copy /y "%~dp0hungphat_autostart.vbs" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\HungPhat_WMS_AutoStart.vbs" >nul 2>&1
    )
)

REM Mo trinh duyet sau khi khoi dong
start "" cmd /c "ping -n 3 127.0.0.1 >nul && start http://localhost:8088"

echo [3/3] May chu da san sang tai http://localhost:8088
echo -------------------------------------------------------------------
echo  * Vui long KHONG DONG cua so nay khi dang lam viec.
echo  * He thong da duoc cai dat tu dong chay ngam khi bat may tinh!
echo -------------------------------------------------------------------
echo.

"%PYTHON_BIN%" app_server.py

pause