@echo off
chcp 65001 >nul
echo 正在清理系统日志 / Windows 更新缓存 / 360 残留（需要管理员）...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0清理-系统日志-管理员.ps1"
echo.
echo 完成，按任意键关闭。
pause >nul
