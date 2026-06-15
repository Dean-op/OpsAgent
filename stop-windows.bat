@echo off
chcp 65001 >nul
echo ====================================
echo Stopping SuperBizAgent services
echo ====================================
echo.

REM Stop FastAPI service.
echo [1/5] Stopping FastAPI service...
taskkill /FI "WINDOWTITLE eq SuperBizAgent API*" /F >nul 2>&1
if errorlevel 1 (
    echo [INFO] FastAPI service is not running or already stopped
) else (
    echo [OK] FastAPI service stopped
)
echo.

REM Stop CLS MCP service.
echo [2/5] Stopping CLS MCP service...
taskkill /FI "WINDOWTITLE eq CLS MCP Server*" /F >nul 2>&1
if errorlevel 1 (
    echo [INFO] CLS MCP service is not running or already stopped
) else (
    echo [OK] CLS MCP service stopped
)
echo.

REM Stop Monitor MCP service.
echo [3/5] Stopping Monitor MCP service...
taskkill /FI "WINDOWTITLE eq Monitor MCP Server*" /F >nul 2>&1
if errorlevel 1 (
    echo [INFO] Monitor MCP service is not running or already stopped
) else (
    echo [OK] Monitor MCP service stopped
)
echo.

REM Clean up MCP port usage as a fallback.
echo [INFO] Cleaning up MCP port usage...
for %%p in (8003 8004) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p" ^| findstr "LISTENING"') do (
        echo [INFO] Port %%p is still used by process %%a. Stopping it...
        taskkill /PID %%a /F >nul 2>&1
    )
)
echo.

REM Stop Docker containers.
echo [4/5] Stopping Milvus container...
docker ps --format "{{.Names}}" | findstr "milvus" >nul 2>&1
if not errorlevel 1 (
    docker compose -f vector-database.yml down
    if errorlevel 1 (
        echo [ERROR] Failed to stop Docker containers
    ) else (
        echo [OK] Milvus container stopped
    )
) else (
    echo [INFO] Milvus container is not running
)
echo.

REM Stop Prometheus container.
echo [5/5] Stopping Prometheus container...
docker ps --format "{{.Names}}" | findstr "super-biz-prometheus" >nul 2>&1
if not errorlevel 1 (
    docker compose -f prometheus-docker.yml down
    if errorlevel 1 (
        echo [ERROR] Failed to stop Prometheus container
    ) else (
        echo [OK] Prometheus container stopped
    )
) else (
    echo [INFO] Prometheus container is not running
)
echo.

echo ====================================
echo All services have been stopped!
echo ====================================
echo.
echo Tip:
echo   - To fully clean Docker volumes, run:
echo     docker compose -f vector-database.yml down -v
echo     docker compose -f prometheus-docker.yml down -v
echo.
pause
