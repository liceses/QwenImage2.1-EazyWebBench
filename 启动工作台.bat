@echo off
setlocal enabledelayedexpansion

rem ============================================================
rem  Qwen-Image-2.1 Local Workbench - launcher
rem  (ASCII-only on purpose: cmd.exe mis-parses CJK inside .bat
rem   under the active OEM codepage. The Chinese UI is in the browser.)
rem
rem  It looks for a Python interpreter in this order:
rem    1) env QWEN21_PY
rem    2) .\python_embeded\python.exe            (bundled portable env)
rem    3) env QWEN21_COMFY_ROOT\python_embeded\python.exe
rem    4) py -3   (Windows Python launcher)
rem    5) python  (on PATH)
rem ============================================================

cd /d "%~dp0"

set "PY="

if defined QWEN21_PY if exist "%QWEN21_PY%" set "PY=%QWEN21_PY%"

if not defined PY if exist "%~dp0python_embeded\python.exe" set "PY=%~dp0python_embeded\python.exe"

if not defined PY if defined QWEN21_COMFY_ROOT if exist "%QWEN21_COMFY_ROOT%\python_embeded\python.exe" set "PY=%QWEN21_COMFY_ROOT%\python_embeded\python.exe"

if not defined PY (
    where py >nul 2>nul && set "PY=py -3"
)

if not defined PY (
    where python >nul 2>nul && set "PY=python"
)

if not defined PY (
    echo.
    echo [X] No Python interpreter found.
    echo     Install Python 3.10+ , or set QWEN21_PY to a python.exe path,
    echo     or point QWEN21_COMFY_ROOT at a ComfyUI portable folder
    echo     ^(which ships python_embeded\python.exe^).
    echo.
    pause
    exit /b 1
)

echo [i] Python: %PY%
echo [i] Project: %~dp0
echo.

rem ------------------------------------------------------------
rem  Preflight: is a workbench ALREADY serving on this port?
rem
rem  On Windows, SO_REUSEADDR lets two processes bind the SAME
rem  host:port, so double-clicking this launcher a second time
rem  prints "started" twice and the kernel then hands each new
rem  connection to an arbitrary one of the two. If one of them is
rem  no longer healthy (its ComfyUI died first, or its console was
rem  closed and it is suspended), the browser shows
rem  "127.0.0.1 did not send any data / ERR_EMPTY_RESPONSE".
rem
rem  So: if the port already answers with our Server header, do NOT
rem  start a second instance -- just open the existing one.
rem ------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8642); $s=$c.GetStream(); $s.ReadTimeout=2000; $b=[Text.Encoding]::ASCII.GetBytes(\"GET /api/config HTTP/1.1`r`nHost: 127.0.0.1:8642`r`nConnection: close`r`n`r`n\"); $s.Write($b,0,$b.Length); $n=$s.Read((New-Object byte[] 4096),0,4096); $c.Close(); if($n -gt 0){ $ok=$true } } catch {}; if($ok){ exit 0 } else { exit 1 }" >nul 2>nul

if not errorlevel 1 (
    echo [i] A workbench is already running on port 8642.
    echo [i] Opening it in your browser instead of starting a second one:
    echo [i]     http://127.0.0.1:8642
    echo [i] Do not double-click this launcher twice - run only one instance.
    start "" "http://127.0.0.1:8642"
    ping -n 3 127.0.0.1 >nul 2>nul
    exit /b 0
)

%PY% "%~dp0server.py" %*

if errorlevel 1 (
    echo.
    echo [X] Workbench exited with an error. See messages above.
    echo     If it says the port is occupied by a stuck instance, either
    echo     kill that process or run:  python server.py --port 8643
    pause
)

endlocal
