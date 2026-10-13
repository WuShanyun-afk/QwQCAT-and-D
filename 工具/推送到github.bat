@echo off
chcp 65001 >nul
title 小鲸鱼要游上 GitHub 啦
cd /d "D:\小鲸鱼的专属文件夹"

echo.
echo   ================================================
echo      🐋  小鲸鱼 → GitHub 推送
echo   ================================================
echo.
echo   正在把作品集推上去，稍等一下...
echo.
echo   ------------------------------------------------
echo.

git add -A
git commit -m "更新：%date% %time%"
git push origin main

echo.
echo   ================================================
if %errorlevel%==0 (
  echo      ✅  推送成功！
  echo.
  echo      线上看这里：https://wushanyun-afk.github.io/QwQCAT-and-D/
  echo      仓库在这里：https://github.com/WuShanyun-afk/QwQCAT-and-D
) else (
  echo      ❌  没成功。
  echo.
  echo      先试试多跑一次这个 bat（网络抽风很常见）。
  echo      要是还不行，把窗口里的红字截图给小D看。
)
echo   ================================================
echo.
echo   按任意键关掉这个窗口...
pause >nul
