@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ====================================
echo Starting SuperBizAgent services
echo ====================================
echo.

REM Check whether uv is installed. Fall back to pip if it is unavailable.
echo [1/6] Checking package manager...
where uv >nul 2>&1
if errorlevel 1 (
    echo [INFO] uv is not installed. Falling back to pip.
    echo [TIP] Install uv for faster setup: pip install uv
    set USE_UV=0
) else (
    echo [OK] uv package manager detected
    set USE_UV=1
)
echo.

REM Ensure the configured Python version is compatible.
echo [2/6] Configuring Python version...
if exist .python-version (
    set /p PYTHON_VERSION=<.python-version
    echo [INFO] Current configured version: !PYTHON_VERSION!
    
    REM Python 3.10 is not compatible with this project.
    echo !PYTHON_VERSION! | findstr /C:"3.10" >nul
    if not errorlevel 1 (
        echo [WARN] Python 3.10 is incompatible. Updating to 3.13...
        echo 3.13> .python-version
        echo [OK] Updated to Python 3.13
    )
) else (
    echo [INFO] Creating .python-version file...
    echo 3.13> .python-version
)
echo.

REM Create or synchronize the virtual environment.
echo [3/6] Creating/synchronizing virtual environment...
if exist .venv\Scripts\python.exe (
    echo [INFO] Virtual environment already exists. Checking updates...
    
    REM Use uv sync when available.
    if "%USE_UV%"=="1" (
        uv sync 2>nul
        if errorlevel 1 (
            echo [WARN] uv sync failed. Updating with pip...
            .venv\Scripts\python.exe -m pip install -e . -q
        ) else (
            echo [OK] uv sync completed
        )
    ) else (
        echo [INFO] Updating dependencies with pip...
        .venv\Scripts\python.exe -m pip install -e . -q
    )
) else (
    echo [INFO] Creating a new virtual environment...
    
    REM Use uv sync when available.
    if "%USE_UV%"=="1" (
        echo [INFO] Trying uv sync...
        uv sync 2>nul
        if not errorlevel 1 (
            echo [OK] Virtual environment created by uv
            goto :venv_created
        )
        echo [WARN] uv sync failed. Falling back to python venv...
    )
    
    REM Create the virtual environment with Python venv.
    echo [INFO] Creating with python -m venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        echo [TIP] Please make sure Python 3.11+ is installed
        pause
        exit /b 1
    )
    
    REM Install project dependencies.
    echo [INFO] Installing project dependencies. This may take a few minutes...
    .venv\Scripts\python.exe -m pip install --upgrade pip -q
    .venv\Scripts\python.exe -m pip install -e . -q
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

:venv_created
echo [OK] Virtual environment is ready
echo.

REM Set the Python command.
set PYTHON_CMD=.venv\Scripts\python.exe

REM Clean up leftover MCP port usage to avoid repeated startup port conflicts.
echo [INFO] Checking MCP port usage...
for %%p in (8003 8004) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p" ^| findstr "LISTENING"') do (
        echo [INFO] Port %%p is used by process %%a. Stopping it...
        taskkill /PID %%a /F >nul 2>&1
    )
)
echo.

REM Start Docker Compose services.
echo [4/7] Starting Milvus vector database...
docker ps --format "{{.Names}}" | findstr "milvus-standalone" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Milvus container is already running
) else (
    docker compose -f vector-database.yml up -d
    if errorlevel 1 (
        echo [ERROR] Docker startup failed. Please make sure Docker Desktop is running
        pause
        exit /b 1
    )
    echo [INFO] Waiting for Milvus to start, 10 seconds...
    timeout /t 10 /nobreak >nul
)
echo [OK] Milvus database is ready
echo.

REM Start Prometheus.
echo [5/7] Starting Prometheus monitoring service...
docker ps --format "{{.Names}}" | findstr "super-biz-prometheus" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Prometheus container is already running
) else (
    docker compose -f prometheus-docker.yml up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start Prometheus. Please check prometheus-docker.yml
        pause
        exit /b 1
    )
    echo [INFO] Waiting for Prometheus to start, 5 seconds...
    timeout /t 5 /nobreak >nul
)
echo [OK] Prometheus monitoring service is ready
echo.

REM Start CLS MCP service.
echo [6/7] Starting CLS MCP service...
start "CLS MCP Server" /min %PYTHON_CMD% mcp_servers/cls_server.py
timeout /t 2 /nobreak >nul
echo [OK] CLS MCP service started
echo.

REM Start Monitor MCP service.
echo [7/7] Starting Monitor MCP service...
start "Monitor MCP Server" /min %PYTHON_CMD% mcp_servers/monitor_server.py
timeout /t 2 /nobreak >nul
echo [OK] Monitor MCP service started
echo.

REM Start FastAPI service.
echo [7/8] Starting FastAPI service...
start "SuperBizAgent API" %PYTHON_CMD% -m uvicorn app.main:app --host 0.0.0.0 --port 9900
echo [INFO] Waiting for service startup, 15 seconds...
timeout /t 15 /nobreak >nul
echo.

REM Check service status and upload documents.
echo.
echo [INFO] Checking service status...
curl -s http://localhost:9900/health >nul 2>&1
if errorlevel 1 (
    echo [WARN] Service may still be starting. Please wait a moment
) else (
    echo [OK] FastAPI service is running
    echo.
    
    REM Upload aiops-docs documents to the vector database through the API.
    echo [8/8] Uploading documents to vector database...
    for %%f in (aiops-docs\*.md) do (
        echo   Uploading: %%~nxf
        curl -s -X POST http://localhost:9900/api/upload -F "file=@%%f" >nul 2>&1
    )
    echo [OK] Document upload completed
)

echo.
echo ====================================
echo Services started successfully!
echo ====================================
echo Web UI: http://localhost:9900
echo API docs: http://localhost:9900/docs
echo Prometheus: http://localhost:9090
echo.
echo Logs:
echo   - FastAPI: logs\app_*.log (Loguru logs, daily rotation)
echo   - CLS MCP: type mcp_cls.log
echo   - Monitor: type mcp_monitor.log
echo Stop services: stop-windows.bat
echo ====================================
pause
