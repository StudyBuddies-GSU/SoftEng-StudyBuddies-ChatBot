@echo off

REM Always run from the directory where this script lives
cd /d "%~dp0"

echo Building Docker containers...
docker compose build

IF ERRORLEVEL 1 (
    echo Docker build failed. Press any key to exit.
    pause >nul
    exit /b 1
)

echo Starting Docker containers...
REM Start docker compose up in a new window so this script can continue
start "Docker Compose" cmd /c "docker compose up"

REM Wait a few seconds for containers to come up
timeout /t 5 /nobreak >nul

echo Opening browser at http://localhost:8501 ...
start "" "http://localhost:8501"

echo Done. You can close this window if you like.
pause >nul


