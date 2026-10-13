@echo off
chcp 65001 >nul
title 小鲸鱼要游上 GitHub 啦
cd /d "D:\小鲸鱼的专属文件夹"

echo.
echo   ================================================
echo      🐋  小鲸鱼 → GitHub 推送
echo   ================================================
echo.
echo   等一下会弹出一个窗口（Git Credential Manager）
echo.
echo     [1] 点「Sign in with browser」/「通过浏览器登录」
echo     [2] 浏览器打开后，点绿色的  Authorize  授权
echo     [3] 回来看到 Success 就成了
echo.
echo   如果没弹窗，看看任务栏有没有闪烁的图标~
echo.
echo   ------------------------------------------------
echo.

git push -u origin main --force

echo.
echo   ================================================
if %errorlevel%==0 (
  echo      ✅  成功！作品集已经上网了
  echo      去看看：https://github.com/WuShanyun-afk/QwQCAT-and-D
) else (
  echo      ❌  没成功，把上面的红字截图给小D看
)
echo   ================================================
echo.
echo   按任意键关掉这个窗口...
pause >nul
