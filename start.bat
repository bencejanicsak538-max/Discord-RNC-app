@echo off
cd /d "%~dp0"
where python >nul 2>nul && (python discord_rpc_app.py) || (py discord_rpc_app.py)
