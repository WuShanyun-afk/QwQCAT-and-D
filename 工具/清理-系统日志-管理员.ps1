# ============================================================
#  小鲸鱼 · 系统日志 + 360 残留清理（需要管理员权限）🐋
#  为什么需要管理员：C:\Windows\Logs、Windows 更新缓存、
#  以及 HKLM 注册表，普通权限删不掉。
#
#  用法：右键同目录的「清理-系统日志-右键以管理员运行.bat」→「以管理员身份运行」，
#        Windows 弹窗点「是」，等它自己跑完，按任意键关闭。
#  安全说明：只删可再生的系统日志/更新缓存，不动个人文件。
# ============================================================

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host '❌ 这个脚本需要管理员权限，请右键「以管理员身份运行」。' -ForegroundColor Red
    exit 1
}

function DirSize($p) {
    if (-not (Test-Path -LiteralPath $p)) { return 0 }
    $s = (Get-ChildItem -LiteralPath $p -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    if ($null -eq $s) { return 0 }
    return $s
}

$freeBefore = (Get-PSDrive C).Free

# ---- 1) 可再生的系统日志 / 更新缓存 ----
$targets = @(
    'C:\Windows\Logs\CBS',
    'C:\Windows\Logs\WindowsUpdate',
    'C:\Windows\Logs\MoSetup',
    'C:\Windows\Logs\NetSetup',
    'C:\Windows\Logs\WinREAgent',
    'C:\Windows\Logs\DISM',
    'C:\Windows\Logs\waasmedic',
    'C:\Windows\Logs\MeasuredBoot',
    'C:\Windows\SoftwareDistribution\Download'
)

Write-Host ''
Write-Host '========== 系统日志 / 更新缓存 =========='
foreach ($t in $targets) {
    $before = DirSize $t
    if ($before -eq 0) { Write-Host ("   --      {0}（空/不存在）" -f $t); continue }
    $failed = 0
    foreach ($it in (Get-ChildItem -LiteralPath $t -Force -ErrorAction SilentlyContinue)) {
        try { Remove-Item -LiteralPath $it.FullName -Recurse -Force -ErrorAction Stop }
        catch { $failed++ }
    }
    $after = DirSize $t
    Write-Host ("  {0,8:N1} MB -> {1,7:N1} MB    {2}" -f ($before/1MB), ($after/1MB), $t)
    if ($failed -gt 0) { Write-Host ("           （{0} 项正在使用，跳过）" -f $failed) }
}

# ---- 2) 360 残留注册表（HKLM 那 4 个） ----
Write-Host ''
Write-Host '========== 360 残留（HKLM 注册表） =========='
$keys360 = @(
    'HKLM:\SOFTWARE\360Safe',
    'HKLM:\SOFTWARE\WOW6432Node\360AlbumViewer',
    'HKLM:\SOFTWARE\WOW6432Node\360Safe',
    'HKLM:\SOFTWARE\WOW6432Node\360se6'
)
foreach ($k in $keys360) {
    if (Test-Path $k) {
        try { Remove-Item -LiteralPath $k -Recurse -Force -ErrorAction Stop; Write-Host "  已删 $k" }
        catch { Write-Host "  没删掉 $k（$($_.Exception.Message)）" }
    } else {
        Write-Host "  已不在 $k"
    }
}

# ---- 3) 结果 ----
$freeAfter = (Get-PSDrive C).Free
Write-Host ''
Write-Host ('========== 这次释放：{0:N1} MB  |  C 盘现在可用：{1:N1} GB ==========' -f (($freeAfter - $freeBefore)/1MB), ($freeAfter/1GB)) -ForegroundColor Green
